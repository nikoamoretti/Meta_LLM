"""
Monitoring Dashboard for Automated Update System
Provides real-time status and metrics for all data sources
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from automated_update_system import AutomatedUpdateSystem
from app.database import SessionLocal
from db.db_models import Model, Benchmark, Score
from sqlalchemy import func

class MonitoringDashboard:
    """Simple monitoring dashboard for the automated update system"""
    
    def __init__(self):
        self.update_system = AutomatedUpdateSystem()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get current database statistics"""
        db = SessionLocal()
        try:
            stats = {
                'total_models': db.query(Model).count(),
                'total_benchmarks': db.query(Benchmark).count(),
                'total_scores': db.query(Score).count(),
                'latest_update': None
            }
            
            # Get latest score update time
            latest_score = db.query(Score).order_by(Score.updated_at.desc()).first()
            if latest_score:
                stats['latest_update'] = latest_score.updated_at.isoformat()
            
            # Get scores by category
            benchmark_categories = db.query(Benchmark.category, func.count(Score.id)).join(Score).group_by(Benchmark.category).all()
            stats['scores_by_category'] = {category: count for category, count in benchmark_categories}
            
            # Get top models by overall composite score
            top_models = db.query(Model.name, Score.normalized_value).join(Score).join(Benchmark).filter(
                Benchmark.name == 'overall_composite'
            ).order_by(Score.normalized_value.desc()).limit(10).all()
            stats['top_models'] = [{'name': name, 'score': score} for name, score in top_models]
            
            return stats
            
        finally:
            db.close()
    
    def format_time_ago(self, timestamp_str: str) -> str:
        """Format time ago in human readable format"""
        if not timestamp_str:
            return "Never"
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now()
            diff = now - timestamp
            
            if diff.days > 0:
                return f"{diff.days} days ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hours ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return "Just now"
        except:
            return "Unknown"
    
    def print_dashboard(self):
        """Print formatted dashboard to console"""
        print("\n" + "=" * 80)
        print("🔍 META LLM AUTOMATED UPDATE SYSTEM - MONITORING DASHBOARD")
        print("=" * 80)
        print(f"📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # System Status
        print("\n📊 SYSTEM STATUS")
        print("-" * 40)
        
        status = self.update_system.get_system_status()
        stats = status['stats']
        
        print(f"Total Updates: {stats['total_updates']}")
        print(f"Successful: {stats['successful_updates']}")
        print(f"Failed: {stats['failed_updates']}")
        
        if stats['total_updates'] > 0:
            success_rate = (stats['successful_updates'] / stats['total_updates']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        if stats['last_update_time']:
            print(f"Last Update: {self.format_time_ago(stats['last_update_time'])}")
        
        # Data Sources Status
        print("\n🔄 DATA SOURCES STATUS")
        print("-" * 40)
        
        for source_key, source_info in status['sources'].items():
            status_icon = "✅" if source_info['enabled'] else "❌"
            last_update = self.format_time_ago(source_info['last_update']) if source_info['last_update'] else "Never"
            
            print(f"{status_icon} {source_info['name']:<25} | {source_info['frequency']:<5} | Last: {last_update}")
            
            if source_info['failure_count'] > 0:
                print(f"   ⚠️  {source_info['failure_count']} recent failures")
        
        # Database Statistics
        print("\n📈 DATABASE STATISTICS")
        print("-" * 40)
        
        db_stats = self.get_database_stats()
        print(f"Models: {db_stats['total_models']:,}")
        print(f"Benchmarks: {db_stats['total_benchmarks']:,}")
        print(f"Scores: {db_stats['total_scores']:,}")
        
        if db_stats['latest_update']:
            print(f"Latest Score Update: {self.format_time_ago(db_stats['latest_update'])}")
        
        # Scores by Category
        if db_stats['scores_by_category']:
            print("\n📊 Scores by Category:")
            for category, count in db_stats['scores_by_category'].items():
                print(f"  {category.capitalize()}: {count:,}")
        
        # Top Models
        if db_stats['top_models']:
            print("\n🏆 Top 5 Models (Overall Composite):")
            for i, model in enumerate(db_stats['top_models'][:5], 1):
                print(f"  {i}. {model['name']:<30} {model['score']:.1f}")
        
        print("\n" + "=" * 80)
    
    def export_status_json(self, filename: str = None):
        """Export current status to JSON file"""
        if not filename:
            filename = f"update_system_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        status = self.update_system.get_system_status()
        db_stats = self.get_database_stats()
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'system_status': status,
            'database_stats': db_stats
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"📄 Status exported to: {filename}")
        return filename
    
    def watch_dashboard(self, interval: int = 30):
        """Watch dashboard with auto-refresh"""
        print("🔄 Starting dashboard watch mode (Ctrl+C to stop)")
        print(f"⏰ Refresh interval: {interval} seconds")
        
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')  # Clear screen
                self.print_dashboard()
                print(f"\n⏰ Next refresh in {interval} seconds... (Ctrl+C to stop)")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Dashboard watch stopped.")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Meta LLM Automated Update System Monitoring Dashboard')
    parser.add_argument('--watch', '-w', action='store_true', help='Watch mode with auto-refresh')
    parser.add_argument('--interval', '-i', type=int, default=30, help='Refresh interval in seconds (default: 30)')
    parser.add_argument('--export', '-e', type=str, help='Export status to JSON file')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of formatted text')
    
    args = parser.parse_args()
    
    dashboard = MonitoringDashboard()
    
    if args.json:
        # Output as JSON
        status = dashboard.update_system.get_system_status()
        db_stats = dashboard.get_database_stats()
        output = {
            'timestamp': datetime.now().isoformat(),
            'system_status': status,
            'database_stats': db_stats
        }
        print(json.dumps(output, indent=2, default=str))
        
    elif args.watch:
        # Watch mode
        dashboard.watch_dashboard(args.interval)
        
    elif args.export:
        # Export mode
        dashboard.export_status_json(args.export)
        dashboard.print_dashboard()
        
    else:
        # Default: show dashboard once
        dashboard.print_dashboard()

if __name__ == "__main__":
    main() 