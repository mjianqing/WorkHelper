from click.testing import CliRunner

from worklog.cli import main


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "WorkLog" in result.output

    def test_today_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["today", "--help"])
        assert result.exit_code == 0

    def test_day_invalid_date(self):
        runner = CliRunner()
        result = runner.invoke(main, ["day", "not-a-date"])
        assert result.exit_code != 0
        assert "无效的日期格式" in result.output
