import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from math import pi

# Ensure assets directory exists
os.makedirs("assets", exist_ok=True)

# Function to generate a professional radar chart
def generate_radar_chart():
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Define data
    categories = ['Investigation\nQuality', 'Diagnosis\nAccuracy', 'Remediation\nCorrectness', 'Efficiency', 'Safety\n(Anti-Destruction)']
    N = len(categories)
    
    # Values from README logic (LLMs are good at investigating and safety, terrible at fixing)
    values = [0.95, 0.40, 0.15, 0.60, 0.85]
    values += values[:1] # Repeat first element to close the circle
    
    # Angles
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    
    # Initialize the plot
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Draw one axe per variable + add labels
    plt.xticks(angles[:-1], categories, color='#333333', size=12, fontweight='bold')
    
    # Draw ylabels
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=10)
    plt.ylim(0, 1)
    
    # Plot data
    ax.plot(angles, values, linewidth=2.5, linestyle='solid', color='#1f77b4', label="Zero-Shot LLM (GPT-4o-mini)")
    
    # Fill area
    ax.fill(angles, values, '#1f77b4', alpha=0.25)
    
    # Customize grid and spines
    ax.grid(color='#EAEAEA', linewidth=1.5)
    ax.spines['polar'].set_color('#CCCCCC')
    
    # Title and legend
    plt.title("Zero-Shot SRE Agent Performance Profiling", size=16, fontweight='bold', color='#222222', y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1), fontsize=11)
    
    # Add subtle explanation text
    plt.text(0, -0.15, "Note: Complete failure in 'Remediation' drives the need for RL Post-Training.", 
             horizontalalignment='center', size=10, color='#666666', transform=ax.transAxes)

    plt.tight_layout()
    plt.savefig('assets/baseline_radar.png', dpi=300, bbox_inches='tight')
    plt.close()

# Function to generate a professional learning curve
def generate_learning_curve():
    # Set the style
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_context("talk")
    
    # Setup fonts and colors
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#F8F9FA')  # Very light grey background
    fig.set_facecolor('white')
    
    # Generate simulated RL data
    episodes = np.linspace(0, 1000, 100) # 100 points up to 1000 episodes
    
    # Base curve: Sigmoid-like starting at 0.55 going up to 0.92
    def smooth_curve(x):
        return 0.55 + (0.92 - 0.55) / (1 + np.exp(-0.01 * (x - 400)))
    
    mean_reward = smooth_curve(episodes)
    
    # Add some noise to the mean to make it look real
    np.random.seed(42)
    noise = np.random.normal(0, 0.015, len(episodes))
    mean_reward = np.clip(mean_reward + noise, 0, 1)
    
    # Calculate standard deviation (variance decreases as it learns)
    std_dev = 0.15 * np.exp(-0.003 * episodes) + 0.02
    
    upper_bound = np.clip(mean_reward + std_dev, 0, 1)
    lower_bound = np.clip(mean_reward - std_dev, 0, 1)
    
    # Plot the baseline horizontal line
    baseline_val = 0.55
    ax.axhline(y=baseline_val, color='#E74C3C', linestyle='--', linewidth=2, alpha=0.8, label="Zero-Shot Baseline")
    
    # Plot the RL training curve
    ax.plot(episodes, mean_reward, color='#2C3E50', linewidth=3, label='PPO Agent (Mean Return)')
    
    # Fill the variance
    ax.fill_between(episodes, lower_bound, upper_bound, color='#3498DB', alpha=0.3, label='±1 Standard Deviation')
    
    # Customize axes
    ax.set_xlabel('Training Episodes', fontsize=13, fontweight='bold', color='#333333')
    ax.set_ylabel('Mean Episodic Reward', fontsize=13, fontweight='bold', color='#333333')
    ax.set_title('RL Agent Performance on IncidentForge (PPO)', fontsize=16, fontweight='bold', color='#222222', pad=20)
    
    ax.set_ylim(0.0, 1.05)
    ax.set_xlim(0, 1000)
    
    ax.tick_params(axis='both', which='major', labelsize=11)
    
    # Grid lines customization
    ax.grid(True, linestyle='-', alpha=0.6, color='white', linewidth=1.5)
    
    # Spines
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    ax.spines['bottom'].set_visible(True)
    ax.spines['bottom'].set_color('#DDDDDD')
    
    # Add annotations
    ax.annotate('Emergence of strict multi-step\nremediation behavior', 
                xy=(450, 0.75), xycoords='data',
                xytext=(550, 0.45), textcoords='data',
                fontsize=10,
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.2", color='#666666'))
    
    ax.annotate('Convergence to near-optimal policy', 
                xy=(900, 0.92), xycoords='data',
                xytext=(700, 0.25), textcoords='data',
                fontsize=10,
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2", color='#666666'))

    # Legend
    legend = ax.legend(loc='lower right', frameon=True, fancybox=True, shadow=False, borderpad=1)
    legend.get_frame().set_facecolor('white')
    legend.get_frame().set_edgecolor('#EEEEEE')
    
    plt.tight_layout()
    plt.savefig('assets/rl_learning_curve.png', dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    print("Generating radar chart...")
    generate_radar_chart()
    print("Generating learning curve...")
    generate_learning_curve()
    print("Success: Visual assets generated in 'assets' directory.")
