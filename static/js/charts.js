// Chart.js configurations and utilities for SAVI Assistant

// Default chart colors for dark theme
const chartColors = {
    primary: ['#007bff', '#6610f2', '#6f42c1', '#e83e8c', '#dc3545', '#fd7e14', '#ffc107', '#28a745', '#20c997', '#17a2b8'],
    background: ['rgba(0, 123, 255, 0.1)', 'rgba(102, 16, 242, 0.1)', 'rgba(111, 66, 193, 0.1)', 'rgba(232, 62, 140, 0.1)', 'rgba(220, 53, 69, 0.1)', 'rgba(253, 126, 20, 0.1)', 'rgba(255, 193, 7, 0.1)', 'rgba(40, 167, 69, 0.1)', 'rgba(32, 201, 151, 0.1)', 'rgba(23, 162, 184, 0.1)'],
    border: ['#007bff', '#6610f2', '#6f42c1', '#e83e8c', '#dc3545', '#fd7e14', '#ffc107', '#28a745', '#20c997', '#17a2b8']
};

// Chart.js default configuration for dark theme
Chart.defaults.color = '#ffffff';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
Chart.defaults.backgroundColor = 'rgba(255, 255, 255, 0.05)';

// Global chart configuration
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.padding = 20;
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(0, 0, 0, 0.8)';
Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
Chart.defaults.plugins.tooltip.bodyColor = '#ffffff';
Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
Chart.defaults.plugins.tooltip.borderWidth = 1;

/**
 * Creates a pie chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {Object} data - Chart data with labels and data arrays
 * @param {string} title - Chart title
 * @returns {Chart} Chart instance
 */
function createPieChart(canvasId, data, title = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element with ID '${canvasId}' not found`);
        return null;
    }

    // Destroy existing chart if it exists
    if (ctx.chart) {
        ctx.chart.destroy();
    }

    const config = {
        type: 'pie',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: title,
                data: data.data || [],
                backgroundColor: chartColors.background.slice(0, data.labels?.length || 0),
                borderColor: chartColors.border.slice(0, data.labels?.length || 0),
                borderWidth: 2,
                hoverBorderWidth: 3,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: !!title,
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: 20
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: R$ ${value.toLocaleString('pt-BR', {minimumFractionDigits: 2})} (${percentage}%)`;
                        }
                    }
                }
            },
            elements: {
                arc: {
                    borderWidth: 2
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1000
            }
        }
    };

    const chart = new Chart(ctx, config);
    ctx.chart = chart; // Store reference for future destruction
    return chart;
}

/**
 * Creates a bar chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {Object} data - Chart data with labels and data arrays
 * @param {string} title - Chart title
 * @returns {Chart} Chart instance
 */
function createBarChart(canvasId, data, title = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element with ID '${canvasId}' not found`);
        return null;
    }

    // Destroy existing chart if it exists
    if (ctx.chart) {
        ctx.chart.destroy();
    }

    const config = {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: title,
                data: data.data || [],
                backgroundColor: chartColors.background[0],
                borderColor: chartColors.border[0],
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false,
                hoverBackgroundColor: chartColors.primary[0],
                hoverBorderColor: '#ffffff',
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: !!title,
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: 20
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y || 0;
                            return `${context.label}: R$ ${value.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 0});
                        },
                        font: {
                            size: 11
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        font: {
                            size: 11
                        }
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    };

    const chart = new Chart(ctx, config);
    ctx.chart = chart; // Store reference for future destruction
    return chart;
}

/**
 * Creates a line chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {Object} data - Chart data with labels and datasets
 * @param {string} title - Chart title
 * @returns {Chart} Chart instance
 */
function createLineChart(canvasId, data, title = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element with ID '${canvasId}' not found`);
        return null;
    }

    // Destroy existing chart if it exists
    if (ctx.chart) {
        ctx.chart.destroy();
    }

    const config = {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: data.datasets?.map((dataset, index) => ({
                label: dataset.label || `Dataset ${index + 1}`,
                data: dataset.data || [],
                borderColor: chartColors.primary[index % chartColors.primary.length],
                backgroundColor: chartColors.background[index % chartColors.background.length],
                borderWidth: 3,
                fill: false,
                tension: 0.3,
                pointBackgroundColor: chartColors.primary[index % chartColors.primary.length],
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointHoverBackgroundColor: '#ffffff',
                pointHoverBorderColor: chartColors.primary[index % chartColors.primary.length]
            })) || []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: !!title,
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: 20
                },
                legend: {
                    position: 'top',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y || 0;
                            return `${context.dataset.label}: R$ ${value.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 0});
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    };

    const chart = new Chart(ctx, config);
    ctx.chart = chart; // Store reference for future destruction
    return chart;
}

/**
 * Creates a doughnut chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {Object} data - Chart data with labels and data arrays
 * @param {string} title - Chart title
 * @returns {Chart} Chart instance
 */
function createDoughnutChart(canvasId, data, title = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element with ID '${canvasId}' not found`);
        return null;
    }

    // Destroy existing chart if it exists
    if (ctx.chart) {
        ctx.chart.destroy();
    }

    const config = {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: title,
                data: data.data || [],
                backgroundColor: chartColors.background.slice(0, data.labels?.length || 0),
                borderColor: chartColors.border.slice(0, data.labels?.length || 0),
                borderWidth: 2,
                hoverBorderWidth: 3,
                hoverBorderColor: '#ffffff',
                cutout: '60%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: !!title,
                    text: title,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: 20
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: R$ ${value.toLocaleString('pt-BR', {minimumFractionDigits: 2})} (${percentage}%)`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1000
            }
        }
    };

    const chart = new Chart(ctx, config);
    ctx.chart = chart; // Store reference for future destruction
    return chart;
}

/**
 * Utility function to format currency for charts
 * @param {number} value - The value to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

/**
 * Utility function to generate random colors
 * @param {number} count - Number of colors to generate
 * @returns {Object} Object with background and border color arrays
 */
function generateColors(count) {
    const colors = [];
    const backgrounds = [];
    const borders = [];
    
    for (let i = 0; i < count; i++) {
        if (i < chartColors.primary.length) {
            colors.push(chartColors.primary[i]);
            backgrounds.push(chartColors.background[i]);
            borders.push(chartColors.border[i]);
        } else {
            // Generate random colors if we need more than predefined
            const hue = (i * 137.508) % 360; // Golden angle approximation
            const color = `hsl(${hue}, 70%, 50%)`;
            const background = `hsla(${hue}, 70%, 50%, 0.1)`;
            colors.push(color);
            backgrounds.push(background);
            borders.push(color);
        }
    }
    
    return {
        colors,
        backgrounds,
        borders
    };
}

/**
 * Destroys all charts on the page
 */
function destroyAllCharts() {
    const canvases = document.querySelectorAll('canvas');
    canvases.forEach(canvas => {
        if (canvas.chart) {
            canvas.chart.destroy();
            canvas.chart = null;
        }
    });
}

/**
 * Resizes all charts on the page
 */
function resizeAllCharts() {
    const canvases = document.querySelectorAll('canvas');
    canvases.forEach(canvas => {
        if (canvas.chart) {
            canvas.chart.resize();
        }
    });
}

// Handle window resize
window.addEventListener('resize', function() {
    resizeAllCharts();
});

/**
 * Creates a doughnut chart specifically for Divinópolis vs BH/Contagem comparison
 * @param {string} canvasId - The ID of the canvas element
 * @param {Object} data - Chart data with labels, data arrays, and formatted values
 * @returns {Chart} Chart instance
 */
function createDivinopolisComparisonChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.error(`Canvas element with ID '${canvasId}' not found`);
        return null;
    }

    // Destroy existing chart if it exists
    if (ctx.chart) {
        ctx.chart.destroy();
    }

    const config = {
        type: 'doughnut',
        data: {
            labels: data.labels || ['Divinópolis', 'BH/Contagem'],
            datasets: [{
                data: data.data || [0, 0],
                backgroundColor: ['#28a745', '#0d6efd'],
                borderColor: ['#28a745', '#0d6efd'],
                borderWidth: 3,
                hoverBorderWidth: 4,
                hoverBorderColor: '#ffffff',
                cutout: '60%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 14,
                            weight: '500'
                        },
                        generateLabels: function(chart) {
                            const originalLabels = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                            const formattedData = data.formatted_data || [];
                            
                            return originalLabels.map((label, index) => {
                                if (formattedData[index]) {
                                    label.text = `${label.text}: ${formattedData[index]}`;
                                }
                                return label;
                            });
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const formattedData = data.formatted_data || [];
                            const value = formattedData[context.dataIndex] || formatCurrency(context.parsed);
                            return `${label}: ${value}`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1000
            }
        }
    };

    const chart = new Chart(ctx, config);
    ctx.chart = chart;
    return chart;
}

// Export functions for global use
window.chartUtils = {
    createPieChart,
    createBarChart,
    createLineChart,
    createDoughnutChart,
    createDivinopolisComparisonChart,
    formatCurrency,
    generateColors,
    destroyAllCharts,
    resizeAllCharts,
    chartColors
};
