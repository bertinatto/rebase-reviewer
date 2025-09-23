from colorprint import print_header, print_success, print_fail, print_warning, colorize


class Reporter:
    """Reporter that shows detailed analysis like the original."""

    def __init__(self):
        self.stats = {"verified": [], "failures": [], "skipped": [], "notices": []}

    def checking(self, commit_hash, message):
        """Show that we're checking a commit."""
        print(f"\n{colorize('Checking commit', 'bold')} {commit_hash[:7]}: {message}")

    def pr_found(self, pr_number, tag):
        """Show PR reference found."""
        print(f"  -> Found UPSTREAM PR reference: PR #{pr_number}. Checking if present in tag {tag}...")

    def pr_in_tag(self, pr_number, tag):
        """Show PR is in tag."""
        print(f"  -> {colorize(f'PR #{pr_number} is present in tag {tag}', 'blue')}. Checking for its presence in source branch...")

    def pr_not_in_tag(self, pr_number, tag):
        """Show PR is not in tag."""
        print(f"  -> {colorize(f'PR #{pr_number} is NOT in tag {tag}', 'warning')}. Checking if it's a locally carried commit...")

    def analyzing_diffs(self):
        """Show diff analysis."""
        print("  -> Found in both branches. Analyzing diffs with Gemini...")

    def verified(self, message, details=""):
        self.stats["verified"].append(message)
        print(f"  -> {colorize('✅ VERIFIED', 'green')}: {details}")

    def failed(self, message, reason):
        self.stats["failures"].append(f"{message}: {reason}")
        print(f"  -> {colorize('❌ FAILURE', 'fail')}: {reason}")

    def skipped(self, message, reason="drop commit"):
        self.stats["skipped"].append(message)
        print(f"  -> {colorize('SKIPPED', 'blue')} ({reason})")

    def notice(self, message, details):
        self.stats["notices"].append(f"{message}: {details}")
        print(f"  -> {colorize('NOTICE', 'warning')}: {details}")

    def print_report(self):
        """Generate final summary like the original."""
        print_header("\n--- Final Review Summary ---")

        verified_count = len(self.stats['verified'])
        print(f"\n{colorize(f'{verified_count} Verified Commits', 'green')}:")
        for msg in self.stats['verified']:
            print(f"  - {msg}")

        failures_count = len(self.stats['failures'])
        print(f"\n{colorize(f'{failures_count} Failures', 'fail')}:")
        for msg in self.stats['failures']:
            print(f"  - {msg}")

        skipped_count = len(self.stats['skipped'])
        print(f"\n{colorize(f'{skipped_count} Skipped Commits', 'blue')}:")
        for msg in self.stats['skipped']:
            print(f"  - {msg}")

        notices_count = len(self.stats['notices'])
        print(f"\n{colorize(f'{notices_count} Notices', 'warning')}:")
        for msg in self.stats['notices']:
            print(f"  - {msg}")

        print_header("\n--- Review Complete ---")

        return len(self.stats['failures']) > 0