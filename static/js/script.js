/* ========================================
   FOREST BIODIVERSITY TRACKER - MAIN SCRIPT
   ======================================== */

// ========== GLOBAL VARIABLES ==========
let biodiversityChart = null;
let speciesChart = null;
let updateInterval = null;
let notificationsEnabled = false;

// ========== DOCUMENT READY ==========
$(document).ready(function() {
    console.log('🌿 Forest Biodiversity Tracker Initialized');
    
    // Initialize all components
    initTooltips();
    initDataTables();
    initRealTimeUpdates();
    initNotifications();
    initDarkMode();
    initCharts();
    initFormValidation();
    initImagePreview();
    
    // Set CSRF token for AJAX requests
    setupCSRFToken();
});

// ========== CSRF TOKEN SETUP ==========
function setupCSRFToken() {
    const csrftoken = getCookie('csrftoken');
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ========== INITIALIZE TOOLTIPS ==========
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// ========== INITIALIZE DATA TABLES ==========
function initDataTables() {
    // Add search functionality to tables
    $('.table').each(function() {
        const tableId = $(this).attr('id');
        if (tableId && !$(this).hasClass('no-search')) {
            const searchInput = $(`<input type="text" class="form-control mb-3" placeholder="🔍 Search table..." style="max-width: 300px;">`);
            $(this).before(searchInput);
            
            searchInput.on('keyup', function() {
                const value = $(this).val().toLowerCase();
                $(`#${tableId} tbody tr`).filter(function() {
                    $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
                });
            });
        }
    });
}

// ========== REAL-TIME UPDATES ==========
function initRealTimeUpdates() {
    // Update dashboard stats every 30 seconds
    if ($('.dashboard-container').length) {
        updateInterval = setInterval(function() {
            updateDashboardStats();
        }, 30000);
    }
}

function updateDashboardStats() {
    $.ajax({
        url: '/api/dashboard-stats/',
        method: 'GET',
        success: function(data) {
            if (data.success) {
                // Update stats without page reload
                $('.stat-number').each(function() {
                    const statType = $(this).closest('.stat-card').find('.stat-label').text().toLowerCase();
                    if (statType.includes('species')) {
                        $(this).text(data.total_species);
                    } else if (statType.includes('observations')) {
                        $(this).text(data.total_observations);
                    }
                });
                
                // Show notification for new observations
                if (data.new_observations > 0) {
                    showToast('New Observation!', `${data.new_observations} new species detected`, 'success');
                }
            }
        },
        error: function(error) {
            console.error('Failed to update dashboard stats:', error);
        }
    });
}

// ========== NOTIFICATIONS ==========
function initNotifications() {
    // Request notification permission
    if ('Notification' in window) {
        Notification.requestPermission().then(function(permission) {
            notificationsEnabled = permission === 'granted';
        });
    }
    
    // Check for new alerts every minute
    if ($('.alerts-container').length || $('.dashboard-container').length) {
        setInterval(checkNewAlerts, 60000);
    }
}

function checkNewAlerts() {
    $.ajax({
        url: '/api/check-alerts/',
        method: 'GET',
        success: function(data) {
            if (data.new_alerts && data.new_alerts.length > 0) {
                // Show browser notification
                if (notificationsEnabled) {
                    data.new_alerts.forEach(function(alert) {
                        new Notification('🌿 Biodiversity Alert', {
                            body: alert.message,
                            icon: '/static/images/alert-icon.png',
                            tag: alert.id
                        });
                    });
                }
                
                // Update alert badge
                const alertBadge = $('.nav-link .badge');
                if (alertBadge.length) {
                    alertBadge.text(data.new_alerts_count);
                    alertBadge.show();
                }
                
                // Show toast notification
                showToast(
                    `${data.new_alerts.length} New Alert${data.new_alerts.length > 1 ? 's' : ''}`,
                    'Please check the alerts page for details',
                    'warning'
                );
            }
        }
    });
}

function showToast(title, message, type = 'info') {
    const toastHTML = `
        <div class="toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info'} border-0 position-fixed bottom-0 end-0 m-3" role="alert" aria-live="assertive" aria-atomic="true" style="z-index: 9999;">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    $('body').append(toastHTML);
    const toast = new bootstrap.Toast($('.toast').last()[0]);
    toast.show();
    
    // Remove toast after hiding
    $('.toast').last().on('hidden.bs.toast', function() {
        $(this).remove();
    });
}

// ========== DARK MODE ==========
function initDarkMode() {
    // Check for saved preference
    const darkMode = localStorage.getItem('darkMode') === 'enabled';
    if (darkMode) {
        $('body').addClass('dark-mode');
        $('#darkModeToggle').prop('checked', true);
    }
    
    // Add dark mode toggle button to navbar
    const toggleButton = `
        <li class="nav-item">
            <div class="form-check form-switch mt-2">
                <input class="form-check-input" type="checkbox" id="darkModeToggle" style="cursor: pointer;">
                <label class="form-check-label text-white" for="darkModeToggle" style="cursor: pointer;">
                    <i class="fas fa-moon"></i>
                </label>
            </div>
        </li>
    `;
    
    $('.navbar-nav:last').append(toggleButton);
    
    $('#darkModeToggle').change(function() {
        if ($(this).is(':checked')) {
            $('body').addClass('dark-mode');
            localStorage.setItem('darkMode', 'enabled');
        } else {
            $('body').removeClass('dark-mode');
            localStorage.setItem('darkMode', 'disabled');
        }
    });
}

// ========== CHARTS ==========
function initCharts() {
    // Initialize biodiversity trend chart
    const trendCanvas = document.getElementById('speciesTrendChart');
    if (trendCanvas) {
        const ctx = trendCanvas.getContext('2d');
        biodiversityChart = new Chart(ctx, {
            type: 'line',
            data: window.chartData || { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff'
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    // Initialize species distribution chart
    const distCanvas = document.getElementById('speciesDistributionChart');
    if (distCanvas) {
        const ctx = distCanvas.getContext('2d');
        speciesChart = new Chart(ctx, {
            type: 'doughnut',
            data: window.distributionData || { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Update chart with new data
function updateCharts(newData) {
    if (biodiversityChart) {
        biodiversityChart.data = newData;
        biodiversityChart.update();
    }
}

// ========== FORM VALIDATION ==========
function initFormValidation() {
    // Add validation to all forms
    $('form').each(function() {
        $(this).on('submit', function(e) {
            let isValid = true;
            
            $(this).find('[required]').each(function() {
                if (!$(this).val()) {
                    isValid = false;
                    $(this).addClass('is-invalid');
                    
                    // Add error message if not exists
                    if (!$(this).next('.invalid-feedback').length) {
                        $(this).after('<div class="invalid-feedback">This field is required.</div>');
                    }
                } else {
                    $(this).removeClass('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showToast('Validation Error', 'Please fill all required fields', 'error');
            }
        });
        
        // Remove invalid class on input
        $(this).find('[required]').on('input', function() {
            if ($(this).val()) {
                $(this).removeClass('is-invalid');
            }
        });
    });
}

// ========== IMAGE PREVIEW ==========
function initImagePreview() {
    $('#imageInput').on('change', function(e) {
        const file = e.target.files[0];
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(event) {
                $('#previewImg').attr('src', event.target.result).show();
                $('#imagePreview').fadeIn();
            };
            reader.readAsDataURL(file);
        }
    });
}

// ========== EXPORT DATA ==========
function exportData(format = 'csv') {
    const data = {
        format: format,
        start_date: $('#startDate').val(),
        end_date: $('#endDate').val()
    };
    
    $.ajax({
        url: '/api/export-data/',
        method: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        success: function(response) {
            if (response.success) {
                // Create download link
                const link = document.createElement('a');
                link.href = response.file_url;
                link.download = `biodiversity_data.${format}`;
                link.click();
                
                showToast('Export Complete', 'Your data has been exported successfully', 'success');
            }
        },
        error: function() {
            showToast('Export Failed', 'Please try again later', 'error');
        }
    });
}

// ========== SEARCH FUNCTIONALITY ==========
function searchSpecies() {
    const searchTerm = $('#speciesSearch').val().toLowerCase();
    
    $('.species-card, .species-row').each(function() {
        const text = $(this).text().toLowerCase();
        if (text.includes(searchTerm)) {
            $(this).show();
            $(this).addClass('fade-in');
        } else {
            $(this).hide();
        }
    });
    
    // Update count
    const visibleCount = $('.species-card:visible, .species-row:visible').length;
    $('#searchCount').text(`${visibleCount} species found`);
}

// ========== FILTER FUNCTIONALITY ==========
function filterByCategory(category) {
    if (category === 'all') {
        $('.species-card, .species-row').show();
    } else {
        $('.species-card, .species-row').each(function() {
            if ($(this).data('category') === category) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    }
}

// ========== AUTO-REFRESH ==========
function toggleAutoRefresh() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
        showToast('Auto-refresh Disabled', 'Dashboard will not update automatically', 'info');
    } else {
        initRealTimeUpdates();
        showToast('Auto-refresh Enabled', 'Dashboard will update every 30 seconds', 'success');
    }
}

// ========== KEYBOARD SHORTCUTS ==========
$(document).keydown(function(e) {
    // Ctrl + U - Open upload page
    if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        window.location.href = '/upload/';
    }
    
    // Ctrl + D - Go to dashboard
    if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        window.location.href = '/';
    }
    
    // Ctrl + S - Search focus
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        $('#speciesSearch, .search-input').focus();
    }
    
    // Escape - Close modals
    if (e.key === 'Escape') {
        $('.modal').modal('hide');
    }
});

// ========== PROGRESS BAR ANIMATION ==========
function animateProgressBars() {
    $('.progress-bar').each(function() {
        const width = $(this).data('width') || $(this).css('width');
        $(this).css('width', '0%');
        setTimeout(() => {
            $(this).css('width', width);
        }, 100);
    });
}

// ========== CONFIRM DIALOG ==========
function confirmAction(message, callback) {
    Swal.fire({
        title: 'Are you sure?',
        text: message,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Yes, proceed!',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed && callback) {
            callback();
        }
    });
}

// ========== LOADING INDICATOR ==========
function showLoading() {
    const loader = `
        <div class="loading-overlay position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" style="background: rgba(0,0,0,0.7); z-index: 9999;">
            <div class="text-center bg-white p-4 rounded-4">
                <div class="spinner-border text-success" style="width: 3rem; height: 3rem;"></div>
                <p class="mt-3 mb-0">Loading...</p>
            </div>
        </div>
    `;
    $('body').append(loader);
}

function hideLoading() {
    $('.loading-overlay').fadeOut(function() {
        $(this).remove();
    });
}

// ========== ERROR HANDLING ==========
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    // Don't show to users in production
    if (window.location.hostname === 'localhost') {
        showToast('JavaScript Error', e.message, 'error');
    }
});

// ========== PAGE VISIBILITY API ==========
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Page became visible again - refresh data
        updateDashboardStats();
        checkNewAlerts();
    }
});

// ========== NETWORK STATUS ==========
window.addEventListener('online', function() {
    showToast('Back Online', 'Your connection has been restored', 'success');
    updateDashboardStats();
});

window.addEventListener('offline', function() {
    showToast('Offline Mode', 'Some features may be unavailable', 'warning');
});

// ========== CLEANUP ==========
$(window).on('beforeunload', function() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});

// ========== PRINT FUNCTION ==========
function printReport() {
    window.print();
}

// ========== SHARE FUNCTION ==========
function shareReport() {
    if (navigator.share) {
        navigator.share({
            title: 'Biodiversity Report',
            text: 'Check out this biodiversity report',
            url: window.location.href
        }).catch(console.error);
    } else {
        // Fallback
        const dummy = document.createElement('textarea');
        dummy.value = window.location.href;
        document.body.appendChild(dummy);
        dummy.select();
        document.execCommand('copy');
        document.body.removeChild(dummy);
        showToast('Link Copied', 'Report URL copied to clipboard', 'success');
    }
}

// ========== EXPORT FUNCTIONS ==========
window.exportData = exportData;
window.printReport = printReport;
window.shareReport = shareReport;
window.searchSpecies = searchSpecies;
window.filterByCategory = filterByCategory;
window.toggleAutoRefresh = toggleAutoRefresh;
window.confirmAction = confirmAction;