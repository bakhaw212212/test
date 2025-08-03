/**
 * IA Vente Facile - JavaScript principal
 * Fonctionnalités interactives et utilitaires
 */

// Configuration globale
const AppConfig = {
    maxFileSize: 16 * 1024 * 1024, // 16MB
    allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
    minFiles: 2,
    maxFiles: 4,
    apiTimeout: 60000, // 60 secondes
    debounceDelay: 300
};

// Utilitaires globaux
const Utils = {
    /**
     * Debounce function pour limiter les appels répétés
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Formatage de la taille des fichiers
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Validation des types de fichiers
     */
    isValidFileType(file) {
        return AppConfig.allowedTypes.includes(file.type.toLowerCase());
    },

    /**
     * Validation de la taille des fichiers
     */
    isValidFileSize(file) {
        return file.size <= AppConfig.maxFileSize;
    },

    /**
     * Génération d'un ID unique
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    /**
     * Animation smooth scroll
     */
    smoothScrollTo(element, offset = 0) {
        const elementPosition = element.offsetTop - offset;
        window.scrollTo({
            top: elementPosition,
            behavior: 'smooth'
        });
    },

    /**
     * Copie dans le presse-papiers avec fallback
     */
    async copyToClipboard(text) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                return true;
            } else {
                // Fallback pour les navigateurs plus anciens
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                const result = document.execCommand('copy');
                document.body.removeChild(textArea);
                return result;
            }
        } catch (err) {
            console.error('Erreur lors de la copie:', err);
            return false;
        }
    },

    /**
     * Vibration tactile si supportée
     */
    vibrate(pattern = 50) {
        if ('vibrate' in navigator) {
            navigator.vibrate(pattern);
        }
    },

    /**
     * Notification toast
     */
    showToast(message, type = 'success', duration = 3000) {
        // Créer le toast si il n'existe pas
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1056';
            document.body.appendChild(toastContainer);
        }

        const toastId = Utils.generateId();
        const toastHtml = `
            <div id="toast-${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <i class="fas fa-${type === 'success' ? 'check-circle text-success' : type === 'error' ? 'exclamation-triangle text-danger' : 'info-circle text-info'} me-2"></i>
                    <strong class="me-auto">${type === 'success' ? 'Succès' : type === 'error' ? 'Erreur' : 'Information'}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(`toast-${toastId}`);
        const toast = new bootstrap.Toast(toastElement, { delay: duration });
        toast.show();

        // Nettoyage automatique
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
};

// Gestionnaire de fichiers drag & drop
class FileDropHandler {
    constructor(dropZoneSelector, fileInputSelector, options = {}) {
        this.dropZone = document.querySelector(dropZoneSelector);
        this.fileInput = document.querySelector(fileInputSelector);
        this.options = { ...AppConfig, ...options };
        this.selectedFiles = [];
        
        this.init();
    }

    init() {
        if (!this.dropZone || !this.fileInput) return;

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Events pour le drag & drop
        this.dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
        this.dropZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.dropZone.addEventListener('drop', this.handleDrop.bind(this));
        this.dropZone.addEventListener('click', () => this.fileInput.click());

        // Event pour l'input file
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
    }

    handleDragOver(e) {
        e.preventDefault();
        this.dropZone.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        if (!this.dropZone.contains(e.relatedTarget)) {
            this.dropZone.classList.remove('drag-over');
        }
    }

    handleDrop(e) {
        e.preventDefault();
        this.dropZone.classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        this.processFiles(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.processFiles(files);
    }

    processFiles(files) {
        // Validation du nombre de fichiers
        if (files.length < this.options.minFiles || files.length > this.options.maxFiles) {
            Utils.showToast(
                `Veuillez sélectionner entre ${this.options.minFiles} et ${this.options.maxFiles} images`,
                'error'
            );
            return;
        }

        // Validation des fichiers
        const invalidFiles = files.filter(file => 
            !Utils.isValidFileType(file) || !Utils.isValidFileSize(file)
        );

        if (invalidFiles.length > 0) {
            const invalidFile = invalidFiles[0];
            let message = 'Fichier non valide: ';
            
            if (!Utils.isValidFileType(invalidFile)) {
                message += `Format ${invalidFile.type} non supporté`;
            } else if (!Utils.isValidFileSize(invalidFile)) {
                message += `Taille trop importante (max ${Utils.formatFileSize(this.options.maxFileSize)})`;
            }
            
            Utils.showToast(message, 'error');
            return;
        }

        this.selectedFiles = files;
        this.displayPreview(files);
        Utils.vibrate(50);
    }

    displayPreview(files) {
        const previewContainer = document.getElementById('imagePreview');
        const previewGrid = document.getElementById('previewContainer');
        
        if (!previewContainer || !previewGrid) return;

        previewGrid.innerHTML = '';

        files.forEach((file, index) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const col = document.createElement('div');
                col.className = 'col-6 col-md-3 mb-2';
                col.innerHTML = `
                    <div class="card animate-fade-in-up" style="animation-delay: ${index * 0.1}s">
                        <div class="position-relative">
                            <img src="${e.target.result}" class="card-img-top" 
                                 style="height: 100px; object-fit: cover;" 
                                 alt="Image ${index + 1}">
                            <span class="position-absolute top-0 start-0 bg-primary text-white rounded-circle d-flex align-items-center justify-content-center" 
                                  style="width: 25px; height: 25px; margin: 5px; font-size: 0.8rem;">
                                ${index + 1}
                            </span>
                            <button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 rounded-circle" 
                                    style="width: 25px; height: 25px; margin: 5px; padding: 0;" 
                                    onclick="fileHandler.removeFile(${index})"
                                    title="Supprimer">
                                <i class="fas fa-times" style="font-size: 0.7rem;"></i>
                            </button>
                        </div>
                        <div class="card-body p-2 text-center">
                            <small class="text-muted">${file.name}</small><br>
                            <small class="text-muted">${Utils.formatFileSize(file.size)}</small>
                        </div>
                    </div>
                `;
                previewGrid.appendChild(col);
            };
            reader.readAsDataURL(file);
        });

        previewContainer.classList.remove('d-none');
        
        // Scroll vers l'aperçu après un délai
        setTimeout(() => {
            Utils.smoothScrollTo(previewContainer, 100);
        }, 300);
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        
        if (this.selectedFiles.length === 0) {
            document.getElementById('imagePreview').classList.add('d-none');
            this.fileInput.value = '';
        } else {
            this.displayPreview(this.selectedFiles);
        }
        
        Utils.vibrate(30);
    }

    getFiles() {
        return this.selectedFiles;
    }
}

// Gestionnaire de copie amélioré
class CopyHandler {
    constructor() {
        this.init();
    }

    init() {
        // Délégation d'événements pour les boutons de copie
        document.addEventListener('click', (e) => {
            if (e.target.closest('.copy-btn')) {
                this.handleCopy(e.target.closest('.copy-btn'));
            }
        });
    }

    async handleCopy(button) {
        const content = button.getAttribute('data-content');
        const contentType = button.getAttribute('data-content-type') || 'text';
        
        if (!content) return;

        try {
            const success = await Utils.copyToClipboard(content);
            
            if (success) {
                this.showCopyFeedback(button, contentType);
                Utils.vibrate(50);
                
                // Notification toast
                const message = contentType === 'title' ? 'Titre copié !' : 
                               contentType === 'full' ? 'Description complète copiée !' : 
                               'Contenu copié !';
                Utils.showToast(message, 'success');
            } else {
                throw new Error('Échec de la copie');
            }
        } catch (err) {
            console.error('Erreur lors de la copie:', err);
            Utils.showToast('Erreur lors de la copie', 'error');
        }
    }

    showCopyFeedback(button, contentType) {
        const originalContent = button.innerHTML;
        const originalClasses = button.className;
        
        // Feedback visuel
        button.innerHTML = '<i class="fas fa-check"></i>';
        button.className = button.className.replace(/btn-outline-\w+/, 'btn-success');
        
        // Restauration après 2 secondes
        setTimeout(() => {
            button.innerHTML = originalContent;
            button.className = originalClasses;
        }, 2000);
    }
}

// Gestionnaire de formulaires
class FormHandler {
    constructor(formSelector) {
        this.form = document.querySelector(formSelector);
        this.init();
    }

    init() {
        if (!this.form) return;
        
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
        this.setupValidation();
    }

    setupValidation() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', this.validateField.bind(this, input));
            input.addEventListener('input', Utils.debounce(this.validateField.bind(this, input), AppConfig.debounceDelay));
        });
    }

    validateField(field) {
        const isValid = field.checkValidity();
        
        // Suppression des classes précédentes
        field.classList.remove('is-valid', 'is-invalid');
        
        // Ajout de la classe appropriée
        if (field.value.trim() !== '') {
            field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        }
        
        return isValid;
    }

    handleSubmit(e) {
        e.preventDefault();
        
        // Validation complète du formulaire
        const isValid = this.validateForm();
        
        if (!isValid) {
            Utils.showToast('Veuillez corriger les erreurs dans le formulaire', 'error');
            return;
        }

        // Si le formulaire contient des fichiers, vérifier leur présence
        if (window.fileHandler) {
            const files = window.fileHandler.getFiles();
            if (files.length < AppConfig.minFiles || files.length > AppConfig.maxFiles) {
                Utils.showToast(
                    `Veuillez sélectionner entre ${AppConfig.minFiles} et ${AppConfig.maxFiles} images`,
                    'error'
                );
                return;
            }
        }

        this.submitForm();
    }

    validateForm() {
        const inputs = this.form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    }

    submitForm() {
        const submitBtn = this.form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Désactivation du bouton et affichage du loading
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Traitement...';
        
        // Affichage du modal de chargement si disponible
        const loadingModal = document.getElementById('loadingModal');
        if (loadingModal) {
            const modal = new bootstrap.Modal(loadingModal);
            modal.show();
        }
        
        // Soumission après un délai pour permettre l'affichage du modal
        setTimeout(() => {
            this.form.submit();
        }, 500);
    }
}

// Gestionnaire d'animations
class AnimationHandler {
    constructor() {
        this.init();
    }

    init() {
        this.observeElements();
        this.setupScrollAnimations();
    }

    observeElements() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in-up');
                }
            });
        }, { threshold: 0.1 });

        // Observer les cartes et autres éléments
        document.querySelectorAll('.card, .feature-box').forEach(el => {
            observer.observe(el);
        });
    }

    setupScrollAnimations() {
        // Animation du navbar au scroll
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            window.addEventListener('scroll', Utils.debounce(() => {
                if (window.scrollY > 100) {
                    navbar.classList.add('navbar-scrolled');
                } else {
                    navbar.classList.remove('navbar-scrolled');
                }
            }, 100));
        }
    }
}

// Gestionnaire de thème (mode sombre/clair)
class ThemeHandler {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.setupThemeToggle();
    }

    setupThemeToggle() {
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', this.toggleTheme.bind(this));
        }
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.currentTheme);
        localStorage.setItem('theme', this.currentTheme);
        Utils.vibrate(50);
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
            }
        }
    }
}

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 IA Vente Facile - Application initialisée');
    
    // Initialisation des gestionnaires
    window.fileHandler = new FileDropHandler('#dropZone', '#files');
    window.copyHandler = new CopyHandler();
    window.formHandler = new FormHandler('#uploadForm');
    window.animationHandler = new AnimationHandler();
    window.themeHandler = new ThemeHandler();
    
    // Gestion des erreurs globales
    window.addEventListener('error', (e) => {
        console.error('Erreur JavaScript:', e.error);
        Utils.showToast('Une erreur inattendue s\'est produite', 'error');
    });
    
    // Gestion des erreurs de promesse non catchées
    window.addEventListener('unhandledrejection', (e) => {
        console.error('Promesse rejetée:', e.reason);
        Utils.showToast('Erreur de communication avec le serveur', 'error');
    });
    
    // Performance monitoring simple
    if ('performance' in window) {
        window.addEventListener('load', () => {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            console.log(`⚡ Page chargée en ${loadTime}ms`);
        });
    }
    
    // Service Worker registration (pour les fonctionnalités offline futures)
    if ('serviceWorker' in navigator && location.protocol === 'https:') {
        navigator.serviceWorker.register('/sw.js').catch(err => {
            console.log('Service Worker non disponible:', err);
        });
    }
});

// Export des utilitaires pour utilisation externe
window.AppUtils = Utils;