// ─── Toast System ───────────────────────────────────────────────────────
const TOAST_CONFIG = {
    success: { icon: '✓', bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', bar: 'bg-emerald-500' },
    error:   { icon: '✕', bg: 'bg-red-50',     border: 'border-red-200',     text: 'text-red-800',     bar: 'bg-red-500'     },
    warning: { icon: '!', bg: 'bg-yellow-50',  border: 'border-yellow-200',  text: 'text-yellow-800',  bar: 'bg-yellow-500'  },
    info:    { icon: 'i', bg: 'bg-blue-50',    border: 'border-blue-200',    text: 'text-blue-800',    bar: 'bg-blue-500'    },
};

function showToast(text, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const cfg = TOAST_CONFIG[type] || TOAST_CONFIG.info;
    const toast = document.createElement('div');
    toast.className = `pointer-events-auto flex items-start gap-3 px-4 py-3.5 rounded-xl shadow-lg border ${cfg.bg} ${cfg.border} ${cfg.text} text-xs font-medium translate-x-16 opacity-0 transition-all duration-300 relative overflow-hidden`;
    
    toast.innerHTML = `
        <span class="flex items-center justify-center w-5 h-5 rounded-full bg-white/80 shadow-sm border border-black/5 font-bold shrink-0">${cfg.icon}</span>
        <span class="flex-1 leading-normal pr-2">${text}</span>
        <div class="absolute bottom-0 left-0 h-0.5 ${cfg.bar} transition-all duration-linear" style="width: 100%; transition-duration: ${duration}ms"></div>
    `;

    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-16', 'opacity-0');
    });

    // Shrink progress bar
    setTimeout(() => {
        const bar = toast.querySelector('.absolute');
        if (bar) bar.style.width = '0%';
    }, 50);

    // Auto-remove toast
    setTimeout(() => {
        toast.classList.add('translate-x-16', 'opacity-0');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, duration);
}

// ─── HTMX & Link Loading Bar ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const loadingBar = document.getElementById('htmx-loading-bar');

    document.addEventListener('htmx:beforeRequest', () => {
        if (loadingBar) {
            loadingBar.style.opacity = '1';
            loadingBar.style.width = '30%';
        }
    });

    document.addEventListener('htmx:afterRequest', () => {
        if (loadingBar) {
            loadingBar.style.width = '100%';
            setTimeout(() => {
                loadingBar.style.opacity = '0';
                loadingBar.style.width = '0%';
            }, 300);
        }
    });

    // Standard non-HTMX Link Loading Bar
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a');
        if (!link) return;
        const href = link.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:') || link.target === '_blank' || link.hasAttribute('download') || link.hasAttribute('hx-get') || link.hasAttribute('hx-post')) {
            return;
        }
        if (href.startsWith('mailto:') || href.startsWith('tel:')) return;
        if (loadingBar) {
            loadingBar.style.opacity = '1';
            loadingBar.style.width = '70%';
            let width = 70;
            const interval = setInterval(() => {
                if (width < 95) {
                    width += 1;
                    loadingBar.style.width = width + '%';
                } else {
                    clearInterval(interval);
                }
            }, 100);
        }
    });

    // Reset loaders and spinners on history navigation (bfcache restore)
    window.addEventListener('pageshow', () => {
        if (loadingBar) {
            loadingBar.style.width = '100%';
            setTimeout(() => {
                loadingBar.style.opacity = '0';
                loadingBar.style.width = '0%';
            }, 100);
        }
        document.querySelectorAll('.btn-loading').forEach(btn => {
            removeSpinner(btn);
        });
    });
});

// ─── Global Button Spinner on submits ───────────────────────────────
function addSpinner(btn) {
    if (btn.classList.contains('btn-loading') || btn.disabled) return;
    btn.dataset.originalHtml = btn.innerHTML;
    
    // Prevent wrapping
    btn.style.whiteSpace = 'nowrap';
    
    const rect = btn.getBoundingClientRect();
    // Add extra space for the spinner icon dynamically
    btn.style.width = (rect.width + 28) + 'px';
    btn.classList.add('btn-loading');
    
    const spinnerSpan = document.createElement('span');
    spinnerSpan.className = 'loading loading-spinner loading-xs mr-1.5';
    btn.prepend(spinnerSpan);
    btn.disabled = true;
}

function removeSpinner(btn) {
    if (!btn || !btn.classList.contains('btn-loading')) return;
    btn.classList.remove('btn-loading');
    const spinner = btn.querySelector('.loading-spinner');
    if (spinner) spinner.remove();
    btn.disabled = false;
    btn.style.width = '';
    btn.style.whiteSpace = '';
}

document.addEventListener('submit', function(e) {
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submitBtn) {
        addSpinner(submitBtn);
    }
});

document.addEventListener('htmx:beforeRequest', function(evt) {
    const elt = evt.detail.elt;
    if (elt) {
        let btn = elt.closest('button, a.btn');
        if (btn) {
            addSpinner(btn);
        } else {
            const submitBtn = elt.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                addSpinner(submitBtn);
            }
        }
    }
});

document.addEventListener('htmx:afterRequest', function(evt) {
    const elt = evt.detail.elt;
    if (elt) {
        let btn = elt.closest('button, a.btn');
        if (btn) {
            removeSpinner(btn);
        } else {
            const submitBtn = elt.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                removeSpinner(submitBtn);
            }
        }
    }
});

// ─── Show/Hide Password on Hold ─────────────────────────────────────────
function showPassword(input, btn) {
    input.type = 'text';
    const eyeIcon = btn.querySelector('.eye-icon');
    const eyeSlashIcon = btn.querySelector('.eye-slash-icon');
    if (eyeIcon) eyeIcon.classList.add('hidden');
    if (eyeSlashIcon) eyeSlashIcon.classList.remove('hidden');
}

function hidePassword(input, btn) {
    input.type = 'password';
    const eyeIcon = btn.querySelector('.eye-icon');
    const eyeSlashIcon = btn.querySelector('.eye-slash-icon');
    if (eyeIcon) eyeIcon.classList.remove('hidden');
    if (eyeSlashIcon) eyeSlashIcon.classList.add('hidden');
}

// ─── Show/Hide Password on Hold (Event Delegation) ───────────────────
let activeToggleBtn = null;
let activeToggleInput = null;

function startPeek(btn) {
    if (!btn) return;
    const wrapper = btn.parentElement;
    const input = wrapper ? wrapper.querySelector('input') : null;
    if (input) {
        activeToggleBtn = btn;
        activeToggleInput = input;
        showPassword(input, btn);
    }
}

function stopPeek() {
    if (activeToggleInput && activeToggleBtn) {
        hidePassword(activeToggleInput, activeToggleBtn);
        activeToggleInput = null;
        activeToggleBtn = null;
    }
}

// Mouse delegation
document.addEventListener('mousedown', function(e) {
    const btn = e.target.closest('.password-toggle-btn');
    if (btn) {
        e.preventDefault();
        startPeek(btn);
    }
});

document.addEventListener('mouseup', function() {
    stopPeek();
});

document.addEventListener('mouseout', function(e) {
    if (activeToggleBtn && !activeToggleBtn.contains(e.target)) {
        stopPeek();
    }
});

// Touch delegation for mobile
document.addEventListener('touchstart', function(e) {
    const btn = e.target.closest('.password-toggle-btn');
    if (btn) {
        e.preventDefault();
        startPeek(btn);
    }
}, { passive: false });

document.addEventListener('touchend', function() {
    stopPeek();
});

document.addEventListener('touchcancel', function() {
    stopPeek();
});

// ─── HTMX Message Toast Notifications ───────────────────────────────────
document.addEventListener('htmxMessages', function(evt) {
    if (Array.isArray(evt.detail)) {
        evt.detail.forEach(msg => {
            const normalizedType = msg.type.includes('error') ? 'error' : msg.type.includes('success') ? 'success' : msg.type.includes('warning') ? 'warning' : 'info';
            showToast(msg.text, normalizedType);
        });
    } else if (evt.detail && evt.detail.text) {
        const normalizedType = evt.detail.type.includes('error') ? 'error' : evt.detail.type.includes('success') ? 'success' : evt.detail.type.includes('warning') ? 'warning' : 'info';
        showToast(evt.detail.text, normalizedType);
    }
});

// Convert Django messages to toasts on page load
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('django-messages');
    if (container) {
        container.querySelectorAll('span[data-text]').forEach(el => {
            const type = el.dataset.type || 'info';
            const normalizedType = type.includes('error') ? 'error' : type.includes('success') ? 'success' : type.includes('warning') ? 'warning' : 'info';
            showToast(el.dataset.text, normalizedType);
        });
    }
});
