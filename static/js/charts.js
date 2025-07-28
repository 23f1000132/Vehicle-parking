// Chart.js configuration and utilities
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

// Color scheme
const colors = {
    primary: '#007bff',
    success: '#28a745',
    danger: '#dc3545',
    warning: '#ffc107',
    info: '#17a2b8',
    light: '#f8f9fa',
    dark: '#343a40'
};

// Utility function to create charts
function createParkingChart(canvasId, data, type = 'bar') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    return new Chart(ctx, {
        type: type,
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Function to update chart data dynamically
function updateChartData(chart, newData) {
    chart.data = newData;
    chart.update();
}

// Auto-refresh functionality (optional)
function enableAutoRefresh(interval = 30000) {
    setInterval(function() {
        if (window.location.pathname.includes('dashboard')) {
            // Only refresh if user is not actively using the page
            if (document.hasFocus() && document.visibilityState === 'visible') {
                location.reload();
            }
        }
    }, interval);
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add any additional chart initialization here
    console.log('Chart.js utilities loaded successfully');
});

// Function to create donut chart for parking overview
function createDonutChart(canvasId, available, occupied, total) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Available', 'Occupied'],
            datasets: [{
                data: [available, occupied],
                backgroundColor: [colors.success, colors.danger],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}
