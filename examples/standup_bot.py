"""
Example: Daily Standup Bot

A simple bot that remembers team updates and generates
standup summaries using Agent Memory Kit.
"""

from datetime import datetime, timedelta
from agent_memory_kit import MemoryManager


class StandupBot:
    """
    A bot that collects daily standup updates and generates summaries.
    
    Features:
    - Remembers each team member's updates
    - Generates daily standup reports
    - Tracks blockers across days
    - Archives old standups
    """
    
    def __init__(self, workspace="./standup_bot"):
        self.memory = MemoryManager(workspace)
        self.team_members = ["Alice", "Bob", "Carol", "David"]
    
    def collect_update(self, member_name, update):
        """
        Collect a standup update from a team member.
        
        Args:
            member_name: Name of the team member
            update: Dict with keys:
                - yesterday: What they completed yesterday
                - today: What they're working on today
                - blockers: Any blockers (optional)
        """
        # Store in HOT layer (today's active updates)
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"standup_{today}_{member_name}"
        
        self.memory.hot(key, {
            "member": member_name,
            "date": today,
            "yesterday": update.get("yesterday"),
            "today": update.get("today"),
            "blockers": update.get("blockers", []),
            "timestamp": datetime.now().isoformat()
        })
        
        # If there are blockers, also track them in WARM
        if update.get("blockers"):
            current_blockers = self.memory.warm("active_blockers") or []
            for blocker in update["blockers"]:
                current_blockers.append({
                    "member": member_name,
                    "blocker": blocker,
                    "date": today
                })
            self.memory.warm("active_blockers", current_blockers)
        
        print(f"✅ Collected update from {member_name}")
    
    def generate_standup_report(self):
        """
        Generate today's standup report.
        
        Returns:
            Formatted standup summary
        """
        today = datetime.now().strftime("%Y-%m-%d")
        updates = []
        
        # Collect all updates from HOT layer
        for member in self.team_members:
            key = f"standup_{today}_{member}"
            update = self.memory.hot(key)
            if update:
                updates.append(update)
        
        if not updates:
            return "No updates collected yet today."
        
        # Generate report
        report_lines = [
            f"📅 Daily Standup - {today}",
            "=" * 40,
            ""
        ]
        
        for update in updates:
            report_lines.extend([
                f"👤 {update['member']}:",
                f"   ✅ Yesterday: {update['yesterday']}",
                f"   🎯 Today: {update['today']}"
            ])
            
            if update['blockers']:
                report_lines.append(f"   🚧 Blockers: {', '.join(update['blockers'])}")
            
            report_lines.append("")
        
        # Add active blockers summary
        active_blockers = self.memory.warm("active_blockers") or []
        recent_blockers = [
            b for b in active_blockers 
            if b["date"] == today
        ]
        
        if recent_blockers:
            report_lines.extend([
                "⚠️ Active Blockers:",
                "-" * 20
            ])
            for blocker in recent_blockers:
                report_lines.append(f"   • {blocker['member']}: {blocker['blocker']}")
        
        report = "\n".join(report_lines)
        
        # Archive to COLD layer
        self.memory.cold(f"standup_report_{today}", {
            "date": today,
            "report": report,
            "updates": updates
        })
        
        return report
    
    def check_yesterday_blockers(self):
        """
        Check if yesterday's blockers were resolved.
        
        Returns:
            List of unresolved blockers
        """
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Get yesterday's standup
        yesterday_standup = self.memory.cold(f"standup_report_{yesterday}")
        
        if not yesterday_standup:
            return "No standup data from yesterday."
        
        yesterday_blockers = []
        for update in yesterday_standup.get("updates", []):
            if update.get("blockers"):
                yesterday_blockers.extend([
                    {"member": update["member"], "blocker": b}
                    for b in update["blockers"]
                ])
        
        if not yesterday_blockers:
            return "No blockers from yesterday."
        
        # Check today's updates for resolutions
        today = datetime.now().strftime("%Y-%m-%d")
        unresolved = []
        
        for blocker_info in yesterday_blockers:
            member = blocker_info["member"]
            key = f"standup_{today}_{member}"
            today_update = self.memory.hot(key)
            
            # Simple check: if blocker not mentioned again, assume resolved
            if today_update:
                today_blockers = today_update.get("blockers", [])
                if blocker_info["blocker"] in today_blockers:
                    unresolved.append(blocker_info)
        
        if unresolved:
            lines = ["🚧 Unresolved Blockers from Yesterday:"]
            for b in unresolved:
                lines.append(f"   • {b['member']}: {b['blocker']}")
            return "\n".join(lines)
        else:
            return "✅ All yesterday's blockers resolved!"
    
    def get_stats(self):
        """Get bot statistics."""
        return self.memory.get_stats()


# Example usage
if __name__ == "__main__":
    bot = StandupBot()
    
    # Collect updates
    bot.collect_update("Alice", {
        "yesterday": "Completed user authentication API",
        "today": "Working on password reset feature",
        "blockers": ["Waiting for design team mockups"]
    })
    
    bot.collect_update("Bob", {
        "yesterday": "Fixed 3 critical bugs",
        "today": "Code review and testing",
        "blockers": []
    })
    
    bot.collect_update("Carol", {
        "yesterday": "Database optimization",
        "today": "Deploying to staging",
        "blockers": ["Need access to production DB"]
    })
    
    # Generate report
    print("\n" + bot.generate_standup_report())
    
    # Check yesterday's blockers
    print("\n" + bot.check_yesterday_blockers())
    
    # Show stats
    print("\n📊 Memory Stats:")
    stats = bot.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
