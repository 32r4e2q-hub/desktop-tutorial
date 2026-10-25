"""Exercise the real publication retry shell block offline, without Git/network writes."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PublishRenderRetryTests(unittest.TestCase):
    def exercise(self, conflict=False):
        source = (ROOT/'production/run_project.sh').read_text()
        block = source[source.index('  push_ok=false'):source.index('  echo "PUBLISHED_COMMIT')]
        # A non-fast-forward push must remain unsuccessful until rebase actually
        # happens; endlessly retrying the same stale push cannot pass this test.
        setup = r'''
set -eu
BRANCH=arena/3c0c229a-desktop-tutorial
synced=0
pushes=0
timeout() { return 0; }
sleep() { return 0; }
git() {
  printf 'GIT %s\n' "$*"
  case "$*" in
    *'push origin HEAD:'*) pushes=$((pushes+1)); test "$synced" = 1 ;;
    *'fetch origin '*) return 0 ;;
    'rebase FETCH_HEAD') REBASE_RESULT ;;
    'rebase --abort') return 0 ;;
    *) return 9 ;;
  esac
}
'''.replace('REBASE_RESULT', 'return 1' if conflict else 'synced=1; return 0')
        return subprocess.run(['bash','-c',setup+'\n'+block+'\necho PUSHES=$pushes'],
                              capture_output=True, text=True, cwd=ROOT)

    def test_branch_advance_rebases_then_publishes_without_overwrite(self):
        result = self.exercise()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('fetch origin arena/3c0c229a-desktop-tutorial',result.stdout)
        self.assertIn('GIT rebase FETCH_HEAD',result.stdout)
        self.assertIn('PUSHES=2',result.stdout)
        self.assertNotIn('--force',result.stdout)
        self.assertNotIn('reset',result.stdout)

    def test_conflict_aborts_and_preserves_local_delivery_for_artifact_recovery(self):
        result = self.exercise(conflict=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('GIT rebase --abort',result.stdout)
        self.assertIn('停止发布',result.stderr)
        self.assertEqual(result.stdout.count('push origin HEAD:'),1)


if __name__ == '__main__':
    unittest.main()
