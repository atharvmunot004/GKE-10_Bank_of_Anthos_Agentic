#!/usr/bin/env python3
"""
Bank of Anthos Investment Platform - Architecture Graph Generator

This script creates a visual graph of the microservices architecture
using Graphviz based on the schema defined in arch_json_schema.txt
"""

import json
import graphviz
from typing import Dict, List, Set
import os

def parse_architecture_schema() -> Dict[str, List[str]]:
    """Parse the architecture schema from the text file."""
    architecture = {}
    
    # Read the schema file
    with open('arch_json_schema.txt', 'r') as f:
        lines = f.readlines()
    
    # Parse the JSON-like structure
    for line in lines:
        line = line.strip()
        if line.startswith('"') and ':' in line:
            # Extract service name and dependencies
            parts = line.split(':', 1)
            service = parts[0].strip().strip('"').strip(',')
            deps_str = parts[1].strip().strip('[').strip(']').strip()
            
            if deps_str:
                # Parse dependencies (handle both simple names and table references)
                deps = []
                for dep in deps_str.split(','):
                    dep = dep.strip().strip('"').strip()
                    if dep:
                        deps.append(dep)
                architecture[service] = deps
            else:
                architecture[service] = []
    
    return architecture

def categorize_services(architecture: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Categorize services by type based on their names and patterns."""
    categories = {
        'frontend': [],
        'application': [],
        'database': [],
        'ai_agent': [],
        'orchestration': []
    }
    
    for service in architecture.keys():
        if service in ['loadgen', 'frontend']:
            categories['frontend'].append(service)
        elif service in ['investment-manager-svc']:
            categories['orchestration'].append(service)
        elif service in ['bank-asset-agent', 'user-tier-agent']:
            categories['ai_agent'].append(service)
        elif any(db in service.lower() for db in ['db', 'database']):
            categories['database'].append(service)
        else:
            categories['application'].append(service)
    
    return categories

def create_architecture_graph(architecture: Dict[str, List[str]]) -> graphviz.Digraph:
    """Create a Graphviz diagram of the microservices architecture."""
    
    # Create the main graph
    dot = graphviz.Digraph(comment='Bank of Anthos Investment Platform Architecture')
    dot.attr(rankdir='TB', size='16,12', dpi='300')
    dot.attr('node', shape='box', style='filled', fontname='Arial', fontsize='10')
    dot.attr('edge', fontname='Arial', fontsize='8')
    
    # Categorize services
    categories = categorize_services(architecture)
    
    # Define colors for different service types
    colors = {
        'frontend': '#FFE6E6',      # Light red
        'application': '#E6F3FF',   # Light blue
        'database': '#E6FFE6',      # Light green
        'ai_agent': '#FFF0E6',      # Light orange
        'orchestration': '#F0E6FF'  # Light purple
    }
    
    # Add nodes with appropriate colors
    for category, services in categories.items():
        for service in services:
            if service in architecture:
                # Clean up service names for display
                display_name = service.replace('-', '\n').replace('_', '\n')
                dot.node(service, display_name, fillcolor=colors[category])
    
    # Add edges (connections)
    for service, dependencies in architecture.items():
        for dep in dependencies:
            # Handle table references (service:table)
            if ':' in dep:
                dep_service = dep.split(':')[0]
            else:
                dep_service = dep
            
            # Only add edge if both nodes exist
            if service in [node for nodes in categories.values() for node in nodes] and \
               dep_service in [node for nodes in categories.values() for node in nodes]:
                dot.edge(service, dep_service)
    
    return dot

def create_layered_graph(architecture: Dict[str, List[str]]) -> graphviz.Digraph:
    """Create a layered graph showing the architecture tiers."""
    
    dot = graphviz.Digraph(comment='Bank of Anthos - Layered Architecture')
    dot.attr(rankdir='TB', size='16,12', dpi='300')
    dot.attr('node', shape='box', style='filled', fontname='Arial', fontsize='9')
    dot.attr('edge', fontname='Arial', fontsize='8', color='gray')
    
    # Define layers (from top to bottom)
    layers = {
        'Testing': ['loadgen'],
        'Presentation': ['frontend'],
        'Orchestration': ['investment-manager-svc'],
        'Application': [
            'userservice', 'contacts', 'ledgerwriter', 'balancereader', 
            'transactionhistory', 'portfolio-reader-svc', 'invest-svc', 
            'withdraw-svc', 'user-request-queue-svc', 'market-reader-svc', 
            'execute-order-svc', 'consistency-manager-svc'
        ],
        'AI Agents': ['user-tier-agent', 'bank-asset-agent'],
        'Data Layer': [
            'account-db', 'ledger-db', 'user-portfolio-db', 
            'queue-db', 'assets-db'
        ]
    }
    
    # Define colors for layers
    layer_colors = {
        'Testing': '#FFCCCC',
        'Presentation': '#CCE5FF', 
        'Orchestration': '#E6CCFF',
        'Application': '#CCFFCC',
        'AI Agents': '#FFE6CC',
        'Data Layer': '#F0F0F0'
    }
    
    # Add nodes grouped by layers
    for layer_name, services in layers.items():
        with dot.subgraph(name=f'cluster_{layer_name}') as c:
            c.attr(style='filled', color='lightgray', fontname='Arial Bold', fontsize='12')
            c.attr(label=layer_name)
            
            for service in services:
                if service in architecture:
                    display_name = service.replace('-', '\n').replace('_', '\n')
                    c.node(service, display_name, fillcolor=layer_colors[layer_name])
    
    # Add edges
    for service, dependencies in architecture.items():
        for dep in dependencies:
            # Handle table references
            if ':' in dep:
                dep_service = dep.split(':')[0]
            else:
                dep_service = dep
            
            # Only add edge if both services exist in our layers
            all_services = [s for services in layers.values() for s in services]
            if service in all_services and dep_service in all_services:
                dot.edge(service, dep_service)
    
    return dot

def create_data_flow_graph(architecture: Dict[str, List[str]]) -> graphviz.Digraph:
    """Create a graph focusing on data flow patterns."""
    
    dot = graphviz.Digraph(comment='Bank of Anthos - Data Flow Architecture')
    dot.attr(rankdir='LR', size='20,12', dpi='300')
    dot.attr('node', shape='ellipse', style='filled', fontname='Arial', fontsize='9')
    dot.attr('edge', fontname='Arial', fontsize='8')
    
    # Define service types and colors
    service_types = {
        'databases': ['account-db', 'ledger-db', 'user-portfolio-db', 'queue-db', 'assets-db'],
        'core_services': ['frontend', 'investment-manager-svc', 'portfolio-reader-svc'],
        'processing_services': ['invest-svc', 'withdraw-svc', 'user-request-queue-svc', 'consistency-manager-svc'],
        'ai_services': ['user-tier-agent', 'bank-asset-agent'],
        'market_services': ['market-reader-svc', 'execute-order-svc'],
        'legacy_services': ['userservice', 'contacts', 'ledgerwriter', 'balancereader', 'transactionhistory']
    }
    
    colors = {
        'databases': '#90EE90',      # Light green
        'core_services': '#87CEEB',  # Sky blue
        'processing_services': '#FFB6C1',  # Light pink
        'ai_services': '#DDA0DD',    # Plum
        'market_services': '#F0E68C', # Khaki
        'legacy_services': '#D3D3D3'  # Light gray
    }
    
    # Add nodes
    for service_type, services in service_types.items():
        for service in services:
            if service in architecture:
                display_name = service.replace('-', '\n').replace('_', '\n')
                dot.node(service, display_name, fillcolor=colors[service_type])
    
    # Add edges with different styles for different types of connections
    for service, dependencies in architecture.items():
        for dep in dependencies:
            if ':' in dep:
                dep_service = dep.split(':')[0]
                table = dep.split(':')[1]
                # Use dotted line for database table access
                dot.edge(service, dep_service, style='dotted', label=f'table: {table}')
            else:
                dep_service = dep
                dot.edge(service, dep_service, style='solid')
    
    return dot

def main():
    """Main function to generate all architecture graphs."""
    
    print("Generating Bank of Anthos Investment Platform Architecture Graphs...")
    
    # Parse architecture schema
    architecture = parse_architecture_schema()
    print(f"Parsed {len(architecture)} services and their dependencies")
    
    # Create different types of graphs
    graphs = {
        'architecture_overview': create_architecture_graph(architecture),
        'layered_architecture': create_layered_graph(architecture),
        'data_flow': create_data_flow_graph(architecture)
    }
    
    # Generate and save graphs
    for graph_name, graph in graphs.items():
        try:
            # Render the graph
            output_file = f'bank_of_anthos_{graph_name}'
            graph.render(output_file, format='png', cleanup=True)
            print(f"✓ Generated {output_file}.png")
            
            # Also generate SVG for better quality
            graph.render(output_file, format='svg', cleanup=True)
            print(f"✓ Generated {output_file}.svg")
            
        except Exception as e:
            print(f"✗ Error generating {graph_name}: {e}")
    
    # Print architecture summary
    print("\n" + "="*60)
    print("ARCHITECTURE SUMMARY")
    print("="*60)
    
    categories = categorize_services(architecture)
    for category, services in categories.items():
        if services:
            print(f"\n{category.upper()}:")
            for service in sorted(services):
                deps = architecture.get(service, [])
                print(f"  • {service} -> {deps}")
    
    print(f"\nTotal Services: {len(architecture)}")
    print(f"Total Connections: {sum(len(deps) for deps in architecture.values())}")
    
    print("\nGraph files generated:")
    print("• bank_of_anthos_architecture_overview.png/svg")
    print("• bank_of_anthos_layered_architecture.png/svg") 
    print("• bank_of_anthos_data_flow.png/svg")

if __name__ == "__main__":
    main()
