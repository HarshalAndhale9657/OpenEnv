// ── Heatmap Generator ──
const heatmapGrid = document.getElementById('heatmap');
for (let i = 0; i < 96; i++) {
    const block = document.createElement('div');
    block.className = 'heat-block healthy';
    if (Math.random() > 0.95) { block.classList.remove('healthy'); block.classList.add('warn'); }
    heatmapGrid.appendChild(block);
}

// ── Clock ──
setInterval(() => {
    document.getElementById('clock').innerText = new Date().toISOString().substring(11, 19) + ' UTC';
}, 1000);

// ── Global Firehose Logs ──
const firehose = document.getElementById('firehose');
let isIncidentActive = false;
let faultyServiceNode = null;

setInterval(() => {
    if(!document.hasFocus() && !simRunning) return; // save CPU
    const line = document.createElement('div');
    line.className = 'fh-line';
    
    const endpoints = ['/api/v1/auth', '/checkout', '/inventory/check', '/user/profile'];
    const ep = endpoints[Math.floor(Math.random() * endpoints.length)];
    
    if (isIncidentActive && Math.random() > 0.3) {
        line.classList.add('err');
        line.innerText = `[${Date.now()}] 500 INTERNAL_ERROR ${ep} duration=${15200 + Math.random()*2000}ms`;
    } else {
        line.innerText = `[${Date.now()}] 200 OK ${ep} duration=${12 + Math.random()*40}ms`;
    }
    
    firehose.prepend(line);
    if (firehose.children.length > 50) firehose.lastChild.remove();
}, 100);

// ── Charts & Gauges ──
const ctxRadar = document.getElementById('rewardChart').getContext('2d');
const rewardChart = new Chart(ctxRadar, {
    type: 'radar',
    data: {
        labels: ['Investigation', 'Diagnosis', 'Remediation', 'Efficiency', 'Safety'],
        datasets: [{
            data: [0, 0, 0, 1.0, 1.0],
            backgroundColor: 'rgba(92, 225, 230, 0.2)', borderColor: '#5ce1e6',
            pointBackgroundColor: '#59d98e', borderWidth: 1
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false,
        scales: { r: { angleLines:{color:'#1a2a3a'}, grid:{color:'#1a2a3a'}, pointLabels:{color:'#728394', font:{size:10, family: "JetBrains Mono"}}, ticks:{display:false, min:0, max:1} } },
        plugins: { legend: { display: false } }
    }
});

function createGauge(id, color) {
    return new Chart(document.getElementById(id).getContext('2d'), {
        type: 'doughnut',
        data: { datasets: [{ data: [20, 80], backgroundColor: [color, '#1a2a3a'], borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: true, cutout: '75%', rotation: -90, circumference: 180, plugins: {tooltip:{enabled:false}} }
    });
}
const gaugeCPU = createGauge('gauge-cpu', '#5ce1e6');
const gaugeRAM = createGauge('gauge-ram', '#f5a623');
const gaugeNET = createGauge('gauge-net', '#59d98e');

function updateGauges(isHigh) {
    const cpu = isHigh ? 85 + Math.random()*10 : 15 + Math.random()*10;
    const ram = isHigh ? 92 + Math.random()*5 : 40 + Math.random()*10;
    const net = isHigh ? 95 + Math.random()*4 : 30 + Math.random()*20;
    gaugeCPU.data.datasets[0].data = [cpu, 100-cpu]; gaugeCPU.update();
    gaugeRAM.data.datasets[0].data = [ram, 100-ram]; gaugeRAM.update();
    gaugeNET.data.datasets[0].data = [net, 100-net]; gaugeNET.update();
}
setInterval(() => updateGauges(isIncidentActive), 1500);

// ── Multi-Scenario Simulation Loop ──
const scenarios = [
    {
        name: "Connection Pool Exhaustion",
        node: "payment-service", alert: "payment-service error rate at 45%",
        steps: [
            { type: 'thought', text: '[Agent] Analyzing topology. payment-service is downstream of order-service.' },
            { type: 'action', text: '> check_logs("payment-service")' },
            { type: 'log', text: '[ERROR] Connection pool exhausted. Waiting: 847.' },
            { type: 'thought', text: '[Agent] Pool exhaustion confirmed. Checking current limits.' },
            { type: 'action', text: '> check_config("payment-service")' },
            { type: 'log', text: 'DB_POOL_MAX_SIZE=10' },
            { type: 'thought', text: '[Agent] Limit is 10. Generating patch to increase bounds.' },
            { type: 'action', text: '> update_config("payment-service", {"DB_POOL_MAX_SIZE": "50"})' },
            { type: 'action', text: '> restart_service("payment-service")' },
            { type: 'reward', text: '+0.45 Remediation Reward. Service recovered.' },
            { type: 'action', text: '> submit_diagnosis("Connection pool exhaustion.")' }
        ]
    },
    {
        name: "Cascading Timeout / Gateway Config",
        node: "api-gateway", alert: "api-gateway dropping 30% of incoming traffic",
        steps: [
            { type: 'thought', text: '[Agent] Tracing 500 errors. Origin appears to be edge layer.' },
            { type: 'action', text: '> check_metrics("api-gateway")' },
            { type: 'log', text: '5xx_rate: 32%, latency_p99: 50ms (fast fail)' },
            { type: 'thought', text: '[Agent] Fast fail indicates local rejection. Checking routing tables.' },
            { type: 'action', text: '> check_config("api-gateway")' },
            { type: 'log', text: 'RATE_LIMIT_BURST=10 (Default was 1000)' },
            { type: 'thought', text: '[Agent] Rate limit misconfigured causing false rejection.' },
            { type: 'action', text: '> update_config("api-gateway", {"RATE_LIMIT_BURST": "1000"})' },
            { type: 'action', text: '> restart_service("api-gateway")' },
            { type: 'reward', text: '+0.50 Remediation Reward.' },
            { type: 'action', text: '> submit_diagnosis("Aggressive rate limiter dropping traffic.")' }
        ]
    },
    {
        name: "Memory Leak",
        node: "notification-service", alert: "notification-service OOMKilled",
        steps: [
            { type: 'thought', text: '[Agent] Node death detected. Assessing memory footprint.' },
            { type: 'action', text: '> check_metrics("notification-service")' },
            { type: 'log', text: 'RAM: 99%, CPU: 12%, Status: Crashloop' },
            { type: 'thought', text: '[Agent] Classical OOM signature. Rolling back to previous stable build.' },
            { type: 'action', text: '> rollback_deploy("notification-service")' },
            { type: 'reward', text: '+0.50 Remediation Reward. Previous image restored.' },
            { type: 'action', text: '> check_metrics("notification-service")' },
            { type: 'log', text: 'RAM: 15%, CPU: 8%, Status: Stable' },
            { type: 'action', text: '> submit_diagnosis("Memory leak in latest deployment.")' }
        ]
    }
];

let simRunning = false;

async function runSimulation() {
    if (simRunning) return;
    simRunning = true;
    
    while(true) {
        for (let s of scenarios) {
            await executeScenario(s);
            await new Promise(r => setTimeout(r, 4000)); // gap between incidents
        }
    }
}

async function executeScenario(scenario) {
    const term = document.getElementById('terminal');
    term.innerHTML = `<div class="log-line success">--- STARTING NEW EPISODE ---</div>`;
    document.getElementById('step-count').innerText = 'Step 0';
    
    // Trigger Incident
    isIncidentActive = true;
    document.getElementById('incident-led').classList.add('active');
    document.getElementById('alert-banner').classList.remove('hidden');
    document.getElementById('alert-text').innerText = scenario.alert;
    
    faultyServiceNode = document.getElementById(scenario.node);
    faultyServiceNode.className = 'node service-node fail';
    
    document.getElementById('latency-val').innerText = '12,400ms';
    document.getElementById('latency-val').classList.add('alert-mode');
    document.getElementById('error-val').innerText = '45.0%';
    document.getElementById('error-val').classList.add('alert-mode');
    
    rewardChart.data.datasets[0].data = [0.1, 0.1, 0.1, 0.9, 1.0];
    rewardChart.update();

    let stepCounter = 0;

    for (let i = 0; i < scenario.steps.length; i++) {
        await new Promise(r => setTimeout(r, 800 + Math.random() * 1200));
        
        const step = scenario.steps[i];
        const line = document.createElement('div');
        line.className = `log-line ${step.type}`;
        
        // Typing effect for thoughts
        if (step.type === 'thought') {
            term.appendChild(line);
            for(let char of step.text) {
                line.innerHTML += char;
                await new Promise(r => setTimeout(r, 10)); // fast type
                term.scrollTop = term.scrollHeight;
            }
        } else {
            line.innerText = step.text;
            term.appendChild(line);
        }
        term.scrollTop = term.scrollHeight;

        if (step.type === 'action') {
            stepCounter++;
            document.getElementById('step-count').innerText = `Step ${stepCounter}`;
            
            // Visual flair for investigation
            if (step.text.includes('check_')) {
                faultyServiceNode.classList.add('investigating');
                setTimeout(() => faultyServiceNode.classList.remove('investigating'), 600);
                rewardChart.data.datasets[0].data[0] += 0.25; 
            }
        }
        
        if (step.text.includes('restart_') || step.text.includes('rollback_')) {
            faultyServiceNode.className = 'node service-node healthy';
            document.getElementById('latency-val').innerText = '45ms';
            document.getElementById('latency-val').classList.remove('alert-mode');
            document.getElementById('error-val').innerText = '0.1%';
            document.getElementById('error-val').classList.remove('alert-mode');
            document.getElementById('alert-banner').classList.add('hidden');
            document.getElementById('incident-led').classList.remove('active');
            isIncidentActive = false;
            rewardChart.data.datasets[0].data[2] = 1.0; 
        }
        
        if (step.text.includes('submit_diagnosis')) {
            rewardChart.data.datasets[0].data[1] = 0.98;
            line.className = 'log-line success';
            line.innerText += " -> SCORE: 0.96";
        }
        
        rewardChart.update();
    }
}

document.getElementById('start-demo-btn').addEventListener('click', () => {
    document.getElementById('start-demo-btn').style.display = 'none';
    runSimulation();
});
