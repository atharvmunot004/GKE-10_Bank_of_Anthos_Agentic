#!/usr/bin/env python3
"""
Bank of Anthos Investment Platform - Enhanced Architecture Diagram Generator

Creates a professional, well-styled architecture diagram using Graphviz
based on the microservices architecture schema.
"""

import json
import graphviz
from typing import Dict, List, Set, Tuple
import os

def parse_architecture_schema() -> Dict[str, List[str]]:
    """Parse the architecture schema from the text file."""
    architecture = {}
    
    with open('arch_json_schema.txt', 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if line.startswith('"') and ':' in line:
            parts = line.split(':', 1)
            service = parts[0].strip().strip('"').strip(',').strip()
            deps_str = parts[1].strip().strip('[').strip(']').strip()
            
            if deps_str:
                deps = []
                for dep in deps_str.split(','):
                    dep = dep.strip().strip('"').strip()
                    if dep:
                        deps.append(dep)
                architecture[service] = deps
            else:
                architecture[service] = []
    
    return architecture

def create_main_architecture_diagram(architecture: Dict[str, List[str]]) -> graphviz.Digraph:
    """Create the main architecture diagram with enhanced styling."""
    
    # Create the main graph
    dot = graphviz.Digraph(comment='Bank of Anthos Investment Platform Architecture')
    dot.attr(rankdir='TB', size='20,16', dpi='300', bgcolor='white')
    dot.attr('node', fontname='Arial', fontsize='11', fontweight='bold')
    dot.attr('edge', fontname='Arial', fontsize='9', color='#666666')
    
    # Define service categories with enhanced styling
    categories = {
        'frontend': {
            'services': ['loadgen', 'frontend'],
            'color': '#FF6B6B',
            'style': 'filled,rounded',
            'shape': 'box'
        },
        'orchestration': {
            'services': ['investment-manager-svc'],
            'color': '#4ECDC4',
            'style': 'filled,rounded',
            'shape': 'box'
        },
        'core_services': {
            'services': ['userservice', 'contacts', 'ledgerwriter', 'balancereader', 'transactionhistory'],
            'color': '#45B7D1',
            'style': 'filled,rounded',
            'shape': 'box'
        },
        'investment_services': {
            'services': ['portfolio-reader-svc', 'invest-svc', 'withdraw-svc', 'user-request-queue-svc', 'consistency-manager-svc'],
            'color': '#96CEB4',
            'style': 'filled,rounded',
            'shape': 'box'
        },
        'market_services': {
            'services': ['market-reader-svc', 'execute-order-svc'],
            'color': '#FFEAA7',
            'style': 'filled,rounded',
            'shape': 'box'
        },
        'ai_agents': {
            'services': ['user-tier-agent', 'bank-asset-agent'],
            'color': '#DDA0DD',
            'style': 'filled,rounded',
            'shape': 'ellipse'
        },
        'databases': {
            'services': ['account-db', 'ledger-db', 'user-portfolio-db', 'queue-db', 'assets-db'],
            'color': '#98D8C8',
            'style': 'filled',
            'shape': 'cylinder'
        }
    }
    
    # Add title
    dot.attr(label='Bank of Anthos Investment Platform\nMicroservices Architecture', 
             fontname='Arial Bold', fontsize='16', fontcolor='#2C3E50')
    
    # Add nodes with category-specific styling
    for category, config in categories.items():
        for service in config['services']:
            if service in architecture:
                # Clean up service names for display
                display_name = service.replace('-', '\n').replace('_', '\n')
                
                # Special styling for databases
                if category == 'databases':
                    display_name = f"{service.replace('-', ' ').replace('_', ' ').title()}\n(Database)"
                
                dot.node(service, display_name, 
                        fillcolor=config['color'], 
                        style=config['style'],
                        shape=config['shape'],
                        fontcolor='white' if category != 'databases' else '#2C3E50',
                        width='1.5', height='1.0')
    
    # Add edges with enhanced styling
    for service, dependencies in architecture.items():
        for dep in dependencies:
            # Handle table references
            if ':' in dep:
                dep_service = dep.split(':')[0]
                table_name = dep.split(':')[1]
                
                # Style database table connections differently
                dot.edge(service, dep_service, 
                        style='dashed', 
                        color='#E74C3C',
                        label=f'table: {table_name}',
                        fontsize='8',
                        fontcolor='#E74C3C')
            else:
                dep_service = dep
                # Determine edge color based on service types
                edge_color = '#3498DB'  # Default blue
                
                # Special colors for different types of connections
                if any(db in dep_service for db in ['db', 'database']):
                    edge_color = '#27AE60'  # Green for database connections
                elif 'agent' in dep_service:
                    edge_color = '#9B59B6'  # Purple for AI agent connections
                elif 'manager' in service:
                    edge_color = '#E67E22'  # Orange for orchestration connections
                
                dot.edge(service, dep_service, 
                        color=edge_color,
                        penwidth='2',
                        arrowhead='open',
                        arrowsize='0.8')
    
    return dot

def create_data_flow_diagram(architecture: Dict[str, List[str]]) -> graphviz.Digraph:
    """Create a data flow focused diagram."""
    
    dot = graphviz.Digraph(comment='Bank of Anthos - Data Flow Architecture')
    dot.attr(rankdir='LR', size='24,12', dpi='300', bgcolor='#FAFAFA')
    dot.attr('node', fontname='Arial', fontsize='10', fontweight='bold')
    dot.attr('edge', fontname='Arial', fontsize='8')
    
    # Define flow layers
    layers = {
        'user_layer': {
            'services': ['loadgen', 'frontend'],
            'color': '#FF6B6B',
            'label': 'User Interface Layer'
        },
        'orchestration_layer': {
            'services': ['investment-manager-svc'],
            'color': '#4ECDC4',
            'label': 'Orchestration Layer'
        },
        'business_layer': {
            'services': ['userservice', 'contacts', 'portfolio-reader-svc', 'invest-svc', 'withdraw-svc'],
            'color': '#45B7D1',
            'label': 'Business Logic Layer'
        },
        'processing_layer': {
            'services': ['user-request-queue-svc', 'consistency-manager-svc', 'market-reader-svc', 'execute-order-svc'],
            'color': '#96CEB4',
            'label': 'Processing Layer'
        },
        'ai_layer': {
            'services': ['user-tier-agent', 'bank-asset-agent'],
            'color': '#DDA0DD',
            'label': 'AI Decision Layer'
        },
        'data_layer': {
            'services': ['account-db', 'ledger-db', 'user-portfolio-db', 'queue-db', 'assets-db'],
            'color': '#98D8C8',
            'label': 'Data Storage Layer'
        }
    }
    
    # Add title
    dot.attr(label='Bank of Anthos - Data Flow Architecture', 
             fontname='Arial Bold', fontsize='14', fontcolor='#2C3E50')
    
    # Add nodes grouped by layers
    for layer_name, config in layers.items():
        with dot.subgraph(name=f'cluster_{layer_name}') as c:
            c.attr(style='filled', color='lightgray', fontname='Arial Bold', fontsize='12')
            c.attr(label=config['label'])
            c.attr(rank='same')
            
            for service in config['services']:
                if service in architecture:
                    display_name = service.replace('-', '\n').replace('_', '\n')
                    c.node(service, display_name, 
                          fillcolor=config['color'], 
                          style='filled,rounded',
                          fontcolor='white',
                          shape='box')
    
    # Add edges
    for service, dependencies in architecture.items():
        for dep in dependencies:
            if ':' in dep:
                dep_service = dep.split(':')[0]
                table_name = dep.split(':')[1]
                dot.edge(service, dep_service, 
                        style='dashed', 
                        color='#E74C3C',
                        label=f'{table_name}',
                        fontsize='7')
            else:
                dep_service = dep
                dot.edge(service, dep_service, 
                        color='#34495E',
                        penwidth='2')
    
    return dot

def create_service_dependency_graph(architecture: Dict[str, List[str]]) -> graphviz.Digraph:
    """Create a focused service dependency graph."""
    
    dot = graphviz.Digraph(comment='Bank of Anthos - Service Dependencies')
    dot.attr(rankdir='TB', size='18,14', dpi='300', bgcolor='white')
    dot.attr('node', fontname='Arial', fontsize='10', fontweight='bold')
    dot.attr('edge', fontname='Arial', fontsize='8')
    
    # Define service importance levels
    importance_levels = {
        'critical': ['frontend', 'investment-manager-svc', 'user-portfolio-db', 'ledger-db'],
        'important': ['invest-svc', 'withdraw-svc', 'portfolio-reader-svc', 'user-request-queue-svc'],
        'supporting': ['market-reader-svc', 'execute-order-svc', 'consistency-manager-svc'],
        'ai_services': ['user-tier-agent', 'bank-asset-agent'],
        'databases': ['account-db', 'queue-db', 'assets-db'],
        'legacy': ['userservice', 'contacts', 'ledgerwriter', 'balancereader', 'transactionhistory']
    }
    
    colors = {
        'critical': '#E74C3C',      # Red
        'important': '#3498DB',     # Blue
        'supporting': '#2ECC71',    # Green
        'ai_services': '#9B59B6',   # Purple
        'databases': '#F39C12',     # Orange
        'legacy': '#95A5A6'         # Gray
    }
    
    # Add title
    dot.attr(label='Bank of Anthos - Service Dependency Map', 
             fontname='Arial Bold', fontsize='14', fontcolor='#2C3E50')
    
    # Add nodes by importance
    for level, services in importance_levels.items():
        for service in services:
            if service in architecture:
                display_name = service.replace('-', '\n').replace('_', '\n')
                
                # Special styling based on importance
                if level == 'critical':
                    shape = 'doubleoctagon'
                    width = '2.0'
                    height = '1.2'
                elif level == 'ai_services':
                    shape = 'ellipse'
                    width = '1.8'
                    height = '1.0'
                elif level == 'databases':
                    shape = 'cylinder'
                    width = '1.6'
                    height = '1.0'
                else:
                    shape = 'box'
                    width = '1.5'
                    height = '0.8'
                
                dot.node(service, display_name,
                        fillcolor=colors[level],
                        style='filled,rounded',
                        shape=shape,
                        fontcolor='white',
                        width=width,
                        height=height)
    
    # Add edges with different weights based on importance
    for service, dependencies in architecture.items():
        for dep in dependencies:
            if ':' in dep:
                dep_service = dep.split(':')[0]
                dot.edge(service, dep_service, 
                        style='dashed', 
                        color='#7F8C8D',
                        penwidth='1')
            else:
                dep_service = dep
                # Determine edge weight based on service importance
                if service in importance_levels['critical'] or dep_service in importance_levels['critical']:
                    penwidth = '3'
                    color = '#E74C3C'
                elif service in importance_levels['important'] or dep_service in importance_levels['important']:
                    penwidth = '2'
                    color = '#3498DB'
                else:
                    penwidth = '1'
                    color = '#95A5A6'
                
                dot.edge(service, dep_service,
                        color=color,
                        penwidth=str(penwidth))
    
    return dot

def main():
    """Generate all architecture diagrams."""
    
    print("🏗️  Generating Bank of Anthos Investment Platform Architecture Diagrams...")
    print("=" * 70)
    
    # Parse architecture
    architecture = parse_architecture_schema()
    print(f"📊 Parsed {len(architecture)} services with their dependencies")
    
    # Create diagrams
    diagrams = {
        'main_architecture': create_main_architecture_diagram(architecture),
        'data_flow': create_data_flow_diagram(architecture),
        'service_dependencies': create_service_dependency_graph(architecture)
    }
    
    # Generate files
    for diagram_name, diagram in diagrams.items():
        try:
            output_file = f'bank_of_anthos_{diagram_name}'
            
            # Generate PNG
            diagram.render(output_file, format='png', cleanup=True)
            print(f"✅ Generated {output_file}.png")
            
            # Generate SVG
            diagram.render(output_file, format='svg', cleanup=True)
            print(f"✅ Generated {output_file}.svg")
            
        except Exception as e:
            print(f"❌ Error generating {diagram_name}: {e}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📈 ARCHITECTURE SUMMARY")
    print("=" * 70)
    
    # Count services by type
    service_types = {
        'Frontend': ['loadgen', 'frontend'],
        'Orchestration': ['investment-manager-svc'],
        'Core Services': ['userservice', 'contacts', 'ledgerwriter', 'balancereader', 'transactionhistory'],
        'Investment Services': ['portfolio-reader-svc', 'invest-svc', 'withdraw-svc', 'user-request-queue-svc', 'consistency-manager-svc'],
        'Market Services': ['market-reader-svc', 'execute-order-svc'],
        'AI Agents': ['user-tier-agent', 'bank-asset-agent'],
        'Databases': ['account-db', 'ledger-db', 'user-portfolio-db', 'queue-db', 'assets-db']
    }
    
    for category, services in service_types.items():
        existing_services = [s for s in services if s in architecture]
        if existing_services:
            print(f"\n🔹 {category}: {len(existing_services)} services")
            for service in existing_services:
                deps = len(architecture.get(service, []))
                print(f"   • {service} ({deps} dependencies)")
    
    total_connections = sum(len(deps) for deps in architecture.values())
    print(f"\n📊 Total: {len(architecture)} services, {total_connections} connections")
    
    print(f"\n🎨 Generated Files:")
    print(f"   • bank_of_anthos_main_architecture.png/svg")
    print(f"   • bank_of_anthos_data_flow.png/svg")
    print(f"   • bank_of_anthos_service_dependencies.png/svg")
    
    print(f"\n💡 Use these diagrams for:")
    print(f"   • System architecture presentations")
    print(f"   • New team member onboarding")
    print(f"   • Troubleshooting and debugging")
    print(f"   • System design discussions")

if __name__ == "__main__":
    main()
