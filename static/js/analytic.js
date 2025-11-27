const ctxLine = document.getElementById('lineChart').getContext('2d');
const lineChart = new Chart(ctxLine, {
  type: 'line',
  data: {
    labels: ['Nov 20', 'Nov 21', 'Nov 22', 'Nov 23', 'Nov 24', 'Nov 25'],
    datasets: [{
      label: 'Invoices Processed',
      data: [50, 70, 65, 90, 80, 120],
      borderColor: '#ffd700',
      backgroundColor: 'rgba(255, 215, 0, 0.2)',
      tension: 0.4
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#fff' } } },
    scales: {
      x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
      y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }
    }
  }
});

const ctxBar = document.getElementById('barChart').getContext('2d');
const barChart = new Chart(ctxBar, {
  type: 'bar',
  data: {
    labels: ['Acme Corp', 'Beta LLC', 'Gamma Inc', 'Delta Co'],
    datasets: [{
      label: 'Amount ($)',
      data: [5400, 2350, 4300, 1250],
      backgroundColor: '#ffd700'
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { labels: { color: '#fff' } } },
    scales: {
      x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
      y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }
    }
  }
});
