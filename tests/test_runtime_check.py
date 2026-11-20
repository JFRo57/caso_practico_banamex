"""La preparación no depende de zonas horarias preinstaladas en el sistema."""
import sys
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfoNotFoundError

from scripts import runtime_check


class RuntimeCheckTests(unittest.TestCase):
    def test_existing_runtime_does_not_install_anything(self):
        with patch.object(sys, 'argv', ['runtime_check']), patch.object(runtime_check, 'check'), patch.object(runtime_check.subprocess, 'run') as run:
            runtime_check.main()
            run.assert_not_called()

    def test_readonly_check_does_not_repair_missing_timezone(self):
        with patch.object(sys, 'argv', ['runtime_check']), patch.object(runtime_check, 'check', side_effect=ZoneInfoNotFoundError('missing')), patch.object(runtime_check.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'zonas horarias'):
                runtime_check.main()
            run.assert_not_called()

    def test_repair_refuses_global_python(self):
        with patch.object(sys, 'argv', ['runtime_check', '--repair']), patch.object(sys, 'prefix', '/global'), patch.object(sys, 'base_prefix', '/global'), patch.object(runtime_check, 'check', side_effect=ZoneInfoNotFoundError('missing')), patch.object(runtime_check.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'paquetes globales'):
                runtime_check.main()
            run.assert_not_called()

    def test_virtual_environment_repairs_then_checks_in_fresh_process(self):
        with patch.object(sys, 'argv', ['runtime_check', '--repair']), patch.object(sys, 'prefix', '/project/venv'), patch.object(sys, 'base_prefix', '/global'), patch.object(runtime_check, 'check', side_effect=ZoneInfoNotFoundError('missing')), patch.object(runtime_check.subprocess, 'run') as run:
            runtime_check.main()
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0][:4], [sys.executable, '-m', 'pip', 'install'])
            self.assertEqual(run.call_args_list[1].args[0], [sys.executable, '-m', 'scripts.runtime_check'])


if __name__ == '__main__':
    unittest.main()
