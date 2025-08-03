#!/usr/bin/env python3
"""
Application Flask complète pour génération de descriptions de vente via IA
Copier-coller ce fichier et renommer en main.py
"""

import os
import logging
import json
import base64
import time
import csv
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from PIL import Image
from openai import OpenAI
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

# ================================
# CONFIGURATION DE L'APPLICATION
# ================================

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

# Création de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration de la base de données
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configuration pour les uploads
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = 'uploads'

# Création du dossier d'upload s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extensions autorisées pour les images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ================================
# MODÈLES DE BASE DE DONNÉES
# ================================

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class GenerationSession(db.Model):
    """Modèle pour sauvegarder les sessions de génération de descriptions"""
    __tablename__ = 'generation_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, index=True)
    platform = db.Column(db.String(50), nullable=False)  # vinted, ebay, etsy, general
    image_count = db.Column(db.Integer, nullable=False)
    image_filenames = db.Column(db.Text)  # JSON array des noms de fichiers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    error_message = db.Column(db.Text)
    
    # Relations
    descriptions = db.relationship('ProductDescription', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'platform': self.platform,
            'image_count': self.image_count,
            'image_filenames': json.loads(self.image_filenames) if self.image_filenames else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'error_message': self.error_message,
            'descriptions_count': len(self.descriptions)
        }

class ProductDescription(db.Model):
    """Modèle pour sauvegarder les descriptions générées"""
    __tablename__ = 'product_descriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('generation_sessions.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_suggestion = db.Column(db.String(100))
    category = db.Column(db.String(100))
    keywords = db.Column(db.Text)  # JSON array des mots-clés
    platform_specific_data = db.Column(db.Text)  # JSON pour données spécifiques à la plateforme
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'title': self.title,
            'description': self.description,
            'price_suggestion': self.price_suggestion,
            'category': self.category,
            'keywords': json.loads(self.keywords) if self.keywords else [],
            'platform_specific_data': json.loads(self.platform_specific_data) if self.platform_specific_data else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_edited': self.is_edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None
        }

class UsageStats(db.Model):
    """Modèle pour suivre les statistiques d'utilisation"""
    __tablename__ = 'usage_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    platform = db.Column(db.String(50), nullable=False)
    generations_count = db.Column(db.Integer, default=0)
    images_processed = db.Column(db.Integer, default=0)
    descriptions_generated = db.Column(db.Integer, default=0)
    api_calls_count = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    
    # Index unique pour éviter les doublons
    __table_args__ = (db.UniqueConstraint('date', 'platform', name='unique_daily_stats'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'platform': self.platform,
            'generations_count': self.generations_count,
            'images_processed': self.images_processed,
            'descriptions_generated': self.descriptions_generated,
            'api_calls_count': self.api_calls_count,
            'errors_count': self.errors_count
        }

# ================================
# SERVICE D'IA OPENAI
# ================================

# Configuration OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY n'est pas configurée dans les variables d'environnement")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=60.0,  # Timeout plus long
    max_retries=3   # Retry en cas d'échec
)

def encode_image_to_base64(image_path):
    """Encode une image en base64 pour l'API OpenAI"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Erreur lors de l'encodage de l'image {image_path}: {e}")
        raise

def generate_product_descriptions(image_paths, platform="general"):
    """
    Génère des descriptions de produit optimisées via GPT-4 Vision
    
    Args:
        image_paths: Liste des chemins vers les images
        platform: Plateforme cible (ebay, vinted, etsy, general)
    
    Returns:
        Liste de dictionnaires contenant les descriptions générées
    """
    try:
        # Encodage des images
        base64_images = []
        for path in image_paths:
            base64_images.append(encode_image_to_base64(path))
        
        # Configuration du prompt selon la plateforme
        platform_configs = {
            "ebay": {
                "style": "professionnel et détaillé",
                "focus": "spécifications techniques, état, authentificité",
                "tone": "vendeur expérimenté"
            },
            "vinted": {
                "style": "décontracté et personnel",
                "focus": "style, taille, occasion d'usage",
                "tone": "amical et accessible"
            },
            "etsy": {
                "style": "créatif et artisanal",
                "focus": "unicité, histoire, fait-main",
                "tone": "artistique et passionné"
            },
            "general": {
                "style": "polyvalent",
                "focus": "description générale complète",
                "tone": "neutre et informatif"
            }
        }
        
        config = platform_configs.get(platform, platform_configs["general"])
        
        # Construction du prompt
        prompt = f"""
        Analyse ces images d'un objet à vendre et génère 6 descriptions de vente optimisées pour la plateforme {platform}.

        Style requis: {config['style']}
        Focus: {config['focus']}
        Ton: {config['tone']}

        Pour chaque description, fournis:
        1. Un titre accrocheur (max 80 caractères)
        2. Une description détaillée (150-300 mots)
        3. 5-8 tags/mots-clés pertinents
        4. Une estimation de prix en euros (optionnel)
        5. L'état de l'objet (neuf, très bon état, bon état, correct, à rénover)
        6. La plateforme cible recommandée

        Analyse l'objet pour identifier:
        - Type/catégorie
        - Marque (si visible)
        - Couleur(s)
        - Matériau(x)
        - Dimensions approximatives
        - État général
        - Détails distinctifs
        - Usage recommandé

        Réponds uniquement en JSON avec ce format:
        {{
            "object_analysis": {{
                "type": "string",
                "brand": "string",
                "colors": ["string"],
                "materials": ["string"],
                "condition": "string",
                "distinctive_features": ["string"]
            }},
            "descriptions": [
                {{
                    "id": 1,
                    "title": "string",
                    "description": "string",
                    "tags": ["string"],
                    "suggested_price": "string",
                    "condition": "string",
                    "platform": "string",
                    "style_variant": "string"
                }}
            ]
        }}
        
        Varie les approches: certaines descriptions courtes et percutantes, d'autres plus détaillées.
        Utilise un français naturel et évite les répétitions.
        """
        
        # Préparation des messages pour l'API
        content_parts: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        
        # Ajout des images au message
        for base64_image in base64_images:
            content_parts.append({
                "type": "image_url", 
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "high"
                }
            })
        
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": content_parts
            }
        ]
        
        # Appel à l'API OpenAI avec gestion d'erreurs améliorée
        # le modèle le plus récent est "gpt-4o" qui a été publié le 13 mai 2024.
        # ne pas changer cela sauf demande explicite de l'utilisateur
        max_retries = 3
        retry_delay = 2
        result = None
        response_content = None
        
        for attempt in range(max_retries):
            try:
                logging.info(f"Tentative {attempt + 1}/{max_retries} d'appel à l'API OpenAI")
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,  # type: ignore
                    max_tokens=4000,
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                response_content = response.choices[0].message.content
                if response_content is None:
                    raise Exception("Réponse vide de l'API OpenAI")
                
                result = json.loads(response_content)
                logging.info("Réponse OpenAI reçue avec succès")
                break
                
            except Exception as e:
                logging.error(f"Erreur tentative {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logging.info(f"Attente de {retry_delay} secondes avant retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
                else:
                    logging.error("Toutes les tentatives ont échoué")
                    raise Exception(f"Échec de l'API OpenAI après {max_retries} tentatives: {e}")
        
        if not result:
            raise Exception("Aucune réponse valide obtenue de l'API")
        
        # Validation et traitement de la réponse
        descriptions = result.get('descriptions', [])
        object_analysis = result.get('object_analysis', {})
        
        if not descriptions:
            raise Exception("Aucune description générée dans la réponse")
        
        # Ajout des informations d'analyse de l'objet à chaque description
        for desc in descriptions:
            desc['object_analysis'] = object_analysis
            desc['generation_timestamp'] = datetime.utcnow().isoformat()
            desc['platform_used'] = platform
        
        logging.info(f"Génération réussie: {len(descriptions)} descriptions créées")
        return descriptions
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération des descriptions: {e}")
        raise

# ================================
# SERVICE DE BASE DE DONNÉES
# ================================

class DatabaseService:
    """Service pour gérer les opérations de base de données"""
    
    @staticmethod
    def create_generation_session(session_id: str, platform: str, image_filenames: List[str]) -> GenerationSession:
        """Crée une nouvelle session de génération"""
        try:
            session = GenerationSession(
                session_id=session_id,
                platform=platform,
                image_count=len(image_filenames),
                image_filenames=json.dumps(image_filenames),
                status='pending'
            )
            db.session.add(session)
            db.session.commit()
            logging.info(f"Session de génération créée: {session_id}")
            return session
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la création de la session: {e}")
            raise
    
    @staticmethod
    def complete_generation_session(session_id: str, descriptions: List[Dict[str, Any]]) -> bool:
        """Marque une session comme terminée et sauvegarde les descriptions"""
        try:
            session = GenerationSession.query.filter_by(session_id=session_id).first()
            if not session:
                logging.error(f"Session non trouvée: {session_id}")
                return False
            
            # Mise à jour de la session
            session.status = 'completed'
            session.completed_at = datetime.utcnow()
            
            # Sauvegarde des descriptions
            for desc_data in descriptions:
                description = ProductDescription(
                    session_id=session.id,
                    title=desc_data.get('title', ''),
                    description=desc_data.get('description', ''),
                    price_suggestion=desc_data.get('suggested_price', ''),
                    category=desc_data.get('object_analysis', {}).get('type', ''),
                    keywords=json.dumps(desc_data.get('tags', [])),
                    platform_specific_data=json.dumps({
                        'condition': desc_data.get('condition', ''),
                        'style_variant': desc_data.get('style_variant', ''),
                        'platform': desc_data.get('platform', ''),
                        'object_analysis': desc_data.get('object_analysis', {})
                    })
                )
                db.session.add(description)
            
            db.session.commit()
            logging.info(f"Session {session_id} terminée avec {len(descriptions)} descriptions")
            
            # Mise à jour des statistiques
            DatabaseService._update_usage_stats(session.platform, len(descriptions), session.image_count)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la finalisation de la session: {e}")
            return False
    
    @staticmethod
    def fail_generation_session(session_id: str, error_message: str) -> bool:
        """Marque une session comme échouée"""
        try:
            session = GenerationSession.query.filter_by(session_id=session_id).first()
            if not session:
                logging.error(f"Session non trouvée: {session_id}")
                return False
            
            session.status = 'failed'
            session.error_message = error_message
            session.completed_at = datetime.utcnow()
            
            db.session.commit()
            logging.info(f"Session {session_id} marquée comme échouée")
            
            # Mise à jour des statistiques d'erreur
            DatabaseService._update_usage_stats(session.platform, 0, session.image_count, has_error=True)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la mise à jour de la session échouée: {e}")
            return False
    
    @staticmethod
    def _update_usage_stats(platform: str, descriptions_count: int, images_count: int, has_error: bool = False):
        """Met à jour les statistiques d'utilisation quotidiennes"""
        try:
            today = date.today()
            
            # Recherche ou création des stats du jour
            stats = UsageStats.query.filter_by(date=today, platform=platform).first()
            
            if not stats:
                stats = UsageStats(
                    date=today,
                    platform=platform,
                    generations_count=0,
                    images_processed=0,
                    descriptions_generated=0,
                    api_calls_count=0,
                    errors_count=0
                )
                db.session.add(stats)
            
            # Mise à jour des compteurs
            stats.generations_count += 1
            stats.images_processed += images_count
            stats.descriptions_generated += descriptions_count
            stats.api_calls_count += 1
            
            if has_error:
                stats.errors_count += 1
            
            db.session.commit()
            logging.info(f"Statistiques mises à jour pour {platform} le {today}")
            
        except IntegrityError:
            # Gestion des conflits de contrainte unique
            db.session.rollback()
            logging.warning(f"Conflit de statistiques pour {platform} le {today}")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Erreur lors de la mise à jour des statistiques: {e}")
    
    @staticmethod
    def get_recent_sessions(limit: int = 20) -> List[GenerationSession]:
        """Récupère les sessions récentes"""
        return GenerationSession.query.order_by(GenerationSession.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_session_details(session_id: str) -> Optional[GenerationSession]:
        """Récupère les détails d'une session spécifique"""
        return GenerationSession.query.filter_by(session_id=session_id).first()
    
    @staticmethod
    def get_usage_statistics(days: int = 30) -> Dict[str, Any]:
        """Récupère les statistiques d'utilisation sur N jours"""
        try:
            from_date = date.today() - datetime.timedelta(days=days)
            
            # Statistiques globales
            total_sessions = GenerationSession.query.filter(GenerationSession.created_at >= from_date).count()
            successful_sessions = GenerationSession.query.filter(
                GenerationSession.created_at >= from_date,
                GenerationSession.status == 'completed'
            ).count()
            
            # Statistiques par plateforme
            platform_stats = db.session.query(
                UsageStats.platform,
                func.sum(UsageStats.generations_count).label('total_generations'),
                func.sum(UsageStats.descriptions_generated).label('total_descriptions'),
                func.sum(UsageStats.images_processed).label('total_images'),
                func.sum(UsageStats.errors_count).label('total_errors')
            ).filter(UsageStats.date >= from_date).group_by(UsageStats.platform).all()
            
            return {
                'period_days': days,
                'total_sessions': total_sessions,
                'successful_sessions': successful_sessions,
                'success_rate': round((successful_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2),
                'platform_breakdown': [
                    {
                        'platform': stat.platform,
                        'generations': stat.total_generations,
                        'descriptions': stat.total_descriptions,
                        'images': stat.total_images,
                        'errors': stat.total_errors
                    }
                    for stat in platform_stats
                ]
            }
            
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {
                'period_days': days,
                'total_sessions': 0,
                'successful_sessions': 0,
                'success_rate': 0,
                'platform_breakdown': []
            }

# ================================
# FONCTIONS UTILITAIRES
# ================================

def allowed_file(filename):
    """Vérifie si le fichier a une extension autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image(image_path, max_size=(1024, 1024)):
    """Redimensionne l'image pour optimiser l'envoi à l'API"""
    try:
        with Image.open(image_path) as img:
            # Convertir en RGB si nécessaire
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionner si nécessaire
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Sauvegarder l'image redimensionnée
            img.save(image_path, 'JPEG', quality=85, optimize=True)
            return True
    except Exception as e:
        logging.error(f"Erreur lors du redimensionnement de l'image: {e}")
        return False

def cleanup_old_files(max_age_hours=24):
    """Nettoie les anciens fichiers uploadés"""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(upload_folder):
            if filename == '.gitkeep':
                continue
                
            file_path = os.path.join(upload_folder, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    logging.info(f"Fichier ancien supprimé: {filename}")
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage des fichiers: {e}")

# ================================
# ROUTES PRINCIPALES
# ================================

@app.route('/')
def index():
    """Page d'accueil avec formulaire d'upload"""
    # Détection mobile simple via User-Agent
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad', 'windows phone'])
    
    if is_mobile:
        return redirect(url_for('mobile_home'))
    
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Traite l'upload des fichiers et génère les descriptions"""
    try:
        # Vérification des fichiers uploadés
        if 'files' not in request.files:
            flash('Aucun fichier sélectionné', 'error')
            return redirect(url_for('index'))
        
        files = request.files.getlist('files')
        platform = request.form.get('platform', 'general')
        
        # Validation du nombre de fichiers
        if len(files) < 2 or len(files) > 4:
            flash('Veuillez sélectionner entre 2 et 4 images', 'error')
            return redirect(url_for('index'))
        
        # Traitement des fichiers
        uploaded_files = []
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                # Nom de fichier sécurisé avec timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = secure_filename(file.filename)
                unique_filename = f"{timestamp}_{filename}"
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Redimensionnement de l'image
                if resize_image(file_path):
                    uploaded_files.append(file_path)
                    logging.info(f"Image uploadée et redimensionnée: {unique_filename}")
                else:
                    flash(f'Erreur lors du traitement de {filename}', 'error')
                    return redirect(url_for('index'))
        
        if len(uploaded_files) < 2:
            flash('Erreur: pas assez d\'images valides uploadées', 'error')
            return redirect(url_for('index'))
        
        # Génération d'un ID de session unique
        session_id = f"session_{int(time.time())}_{len(uploaded_files)}"
        session['current_session_id'] = session_id
        
        # Création de la session en base de données
        filenames = [os.path.basename(path) for path in uploaded_files]
        db_session = DatabaseService.create_generation_session(session_id, platform, filenames)
        
        try:
            # Génération des descriptions via IA
            descriptions = generate_product_descriptions(uploaded_files, platform)
            
            # Sauvegarde des résultats en base
            if DatabaseService.complete_generation_session(session_id, descriptions):
                # Stockage des résultats dans la session Flask pour affichage immédiat
                session['generated_descriptions'] = descriptions
                session['generation_platform'] = platform
                session['uploaded_images'] = filenames
                
                flash(f'{len(descriptions)} descriptions générées avec succès!', 'success')
                return redirect(url_for('results'))
            else:
                raise Exception("Erreur lors de la sauvegarde en base de données")
                
        except Exception as e:
            # Marquer la session comme échouée
            DatabaseService.fail_generation_session(session_id, str(e))
            flash(f'Erreur lors de la génération: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        logging.error(f"Erreur lors de l'upload: {e}")
        flash('Erreur lors du traitement des fichiers', 'error')
        return redirect(url_for('index'))

@app.route('/results')
def results():
    """Affiche les résultats de génération"""
    descriptions = session.get('generated_descriptions', [])
    platform = session.get('generation_platform', 'general')
    images = session.get('uploaded_images', [])
    
    if not descriptions:
        flash('Aucune description disponible', 'warning')
        return redirect(url_for('index'))
    
    # Détection mobile
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad', 'windows phone'])
    
    if is_mobile:
        return render_template('mobile_results.html', 
                             descriptions=descriptions, 
                             platform=platform, 
                             images=images)
    
    return render_template('results.html', 
                         descriptions=descriptions, 
                         platform=platform, 
                         images=images)

@app.route('/history')
def history():
    """Page d'historique des générations"""
    # Récupération des sessions récentes
    recent_sessions = DatabaseService.get_recent_sessions(50)
    
    # Statistiques d'utilisation
    stats_7_days = DatabaseService.get_usage_statistics(7)
    stats_30_days = DatabaseService.get_usage_statistics(30)
    
    return render_template('history.html', 
                         sessions=recent_sessions,
                         stats_7_days=stats_7_days,
                         stats_30_days=stats_30_days)

# ================================
# ROUTES MOBILES
# ================================

@app.route('/mobile')
def mobile_home():
    """Page d'accueil mobile optimisée"""
    return render_template('mobile_home.html')

@app.route('/mobile/gallery')
def mobile_gallery():
    """Galerie mobile pour sélection des images"""
    return render_template('mobile_gallery.html')

@app.route('/mobile/settings')
def mobile_settings():
    """Page de paramètres mobile"""
    return render_template('mobile_settings.html')

# ================================
# ROUTES API
# ================================

@app.route('/api/session/<session_id>')
def api_session_details(session_id):
    """API pour récupérer les détails d'une session"""
    try:
        session_data = DatabaseService.get_session_details(session_id)
        if not session_data:
            return jsonify({'error': 'Session non trouvée'}), 404
        
        # Récupération des descriptions associées
        descriptions = [desc.to_dict() for desc in session_data.descriptions]
        
        response = session_data.to_dict()
        response['descriptions'] = descriptions
        
        return jsonify(response)
    except Exception as e:
        logging.error(f"Erreur API session details: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/stats')
def api_statistics():
    """API pour récupérer les statistiques d'utilisation"""
    try:
        days = request.args.get('days', 30, type=int)
        stats = DatabaseService.get_usage_statistics(days)
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Erreur API statistics: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/export/csv')
def export_csv():
    """Export des descriptions en CSV"""
    try:
        descriptions = session.get('generated_descriptions', [])
        if not descriptions:
            flash('Aucune description à exporter', 'warning')
            return redirect(url_for('index'))
        
        # Création du CSV en mémoire
        output = io.StringIO()
        writer = csv.writer(output)
        
        # En-têtes
        writer.writerow(['ID', 'Titre', 'Description', 'Tags', 'Prix suggéré', 'État', 'Plateforme'])
        
        # Données
        for i, desc in enumerate(descriptions, 1):
            writer.writerow([
                i,
                desc.get('title', ''),
                desc.get('description', ''),
                ', '.join(desc.get('tags', [])),
                desc.get('suggested_price', ''),
                desc.get('condition', ''),
                desc.get('platform', '')
            ])
        
        # Préparation de la réponse
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=descriptions.csv'}
        )
        
    except Exception as e:
        logging.error(f"Erreur export CSV: {e}")
        flash('Erreur lors de l\'export CSV', 'error')
        return redirect(url_for('results'))

@app.route('/export/json')
def export_json():
    """Export des descriptions en JSON"""
    try:
        descriptions = session.get('generated_descriptions', [])
        if not descriptions:
            flash('Aucune description à exporter', 'warning')
            return redirect(url_for('index'))
        
        # Préparation des données
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'platform': session.get('generation_platform', 'general'),
            'total_descriptions': len(descriptions),
            'descriptions': descriptions
        }
        
        return Response(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=descriptions.json'}
        )
        
    except Exception as e:
        logging.error(f"Erreur export JSON: {e}")
        flash('Erreur lors de l\'export JSON', 'error')
        return redirect(url_for('results'))

# ================================
# INITIALISATION DE L'APPLICATION
# ================================

# Initialisation de la base de données
db.init_app(app)

# Création des tables de base de données
with app.app_context():
    try:
        db.create_all()
        logging.info("Tables de base de données créées avec succès")
    except Exception as e:
        logging.error(f"Erreur lors de la création des tables: {e}")

# Nettoyage périodique des anciens fichiers
import atexit
atexit.register(lambda: cleanup_old_files(24))

# ================================
# POINT D'ENTRÉE
# ================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)