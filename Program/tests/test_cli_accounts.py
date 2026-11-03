"""Settings > Models: the Claude Code and Codex accounts on this computer (claude, claude2, codex2…)."""
import asyncio
import os
import stat
import sys

import pytest

from companion.providers import cli_accounts, codex
from companion.providers.scheduling import resource_for


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    (home / 'bin').mkdir(parents=True)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    monkeypatch.setenv('PATH', str(home / 'bin'))
    return home


def program(path, text=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def by_command(accounts):
    return {(account['provider'], name): account for account in accounts for name in account['commands']}


def test_wrapper_scripts_on_path_name_their_account_folders(home):
    program(home / 'bin' / 'claude')
    program(home / 'bin' / 'claude.cmd', '@"%~dp0\\node.exe" "%~dp0\\node_modules\\claude\\cli.js" %*\n')
    program(home / 'bin' / 'claude2.cmd', '@echo off\nset "CLAUDE_CONFIG_DIR=%USERPROFILE%\\.claude-account2"\nclaude %*\n')
    program(home / 'bin' / 'claude-work.ps1', '$env:CLAUDE_CONFIG_DIR = "$HOME/.claude-work"\n& claude @args\n')
    program(home / 'bin' / 'codex2', '#!/bin/sh\nCODEX_HOME="$HOME/.codex-second" exec codex "$@"\n')
    program(home / 'bin' / 'claude-helper.sh', 'echo nothing to see\n')
    program(home / 'bin' / 'claude3.exe', '')
    found = by_command(cli_accounts.found_accounts())
    assert set(found) == {('claude_code', 'claude'), ('claude_code', 'claude2'), ('claude_code', 'claude-work'),
                          ('codex', 'codex2')}
    assert found[('claude_code', 'claude')]['account_dir'] == ''
    assert found[('claude_code', 'claude2')]['account_dir'] == f'{home}\\.claude-account2'
    assert found[('claude_code', 'claude-work')]['account_dir'] == f'{home}/.claude-work'
    assert found[('codex', 'codex2')]['account_dir'] == f'{home}/.codex-second'
    assert [account['commands'][0] for account in cli_accounts.found_accounts()][0] == 'claude'


def test_powershell_functions_and_aliases_and_shell_aliases_are_read(home):
    program(home / 'Documents' / 'PowerShell' / 'Microsoft.PowerShell_profile.ps1', '\n'.join([
        'function claude2 {',
        '    $env:CLAUDE_CONFIG_DIR = "C:\\Users\\Jim\\.claude-account2"',
        '    if ($true) { claude @args }',
        '}',
        f'function Use-SecondCodex {{ $env:CODEX_HOME = \'{home}/codex two\'; codex @args }}',
        'Set-Alias -Name codex2 -Value Use-SecondCodex',
        'function claude-reset { $env:CLAUDE_CONFIG_DIR = $null }',
    ]))
    program(home / '.bashrc', f"alias claude-alt='CLAUDE_CONFIG_DIR={home}/claude-alt claude'\n")
    found = by_command(cli_accounts.found_accounts())
    if os.name != 'nt':
        # A Windows path is not a full path off Windows; the scan only keeps folders this computer can use.
        assert ('claude_code', 'claude2') not in found
    assert found[('codex', 'codex2')]['account_dir'] == f'{home}/codex two'
    assert found[('claude_code', 'claude-alt')]['account_dir'] == f'{home}/claude-alt'
    assert ('claude_code', 'claude-reset') not in found


def test_a_windows_function_keeps_its_windows_folder(home, monkeypatch):
    monkeypatch.setattr(cli_accounts.os.path, 'isabs', lambda value: True)
    assert cli_accounts.folder_in('$env:CLAUDE_CONFIG_DIR="C:\\Users\\Jim\\.claude-account2"; claude',
                                  'CLAUDE_CONFIG_DIR') == 'C:\\Users\\Jim\\.claude-account2'
    assert cli_accounts.folder_in('set CLAUDE_CONFIG_DIR=C:\\Users\\Jim\\My Claude\r\nclaude %*',
                                  'CLAUDE_CONFIG_DIR') == 'C:\\Users\\Jim\\My Claude'


def test_folders_in_home_are_found_by_name_and_join_their_command(home):
    program(home / '.claude-account2' / 'notes.txt', '')
    (home / '.claude-empty').mkdir()
    (home / '.claude').mkdir()
    (home / '.codex-work').mkdir()
    program(home / '.claude-file', '')
    program(home / 'bin' / 'claude2.bat', f'set CLAUDE_CONFIG_DIR={home}/.claude-account2\nclaude %*\n')
    accounts = cli_accounts.found_accounts()
    folders = {(account['provider'], account['account_dir']): account for account in accounts}
    assert set(folders) == {('claude_code', f'{home}/.claude-account2'), ('claude_code', str(home / '.claude-empty')),
                            ('codex', str(home / '.codex-work'))}
    assert folders[('claude_code', f'{home}/.claude-account2')]['commands'] == ['claude2']
    assert not folders[('claude_code', f'{home}/.claude-account2')]['guess']
    assert folders[('codex', str(home / '.codex-work'))]['guess']


def test_nothing_inside_an_account_folder_is_opened_or_looked_for(home, monkeypatch):
    """The CLI keeps its sign-in in the account folder, so the scan never touches anything inside one."""
    for folder in ('.claude-account2', '.codex-work'):
        program(home / folder / 'sign-in', 'secret')
    program(home / 'bin' / 'claude2.cmd', f'set CLAUDE_CONFIG_DIR={home}/.claude-account2\nclaude %*\n')
    touched = []
    for name in ('is_file', 'read_bytes', 'read_text', 'open', 'stat', 'exists', 'iterdir'):
        original = getattr(cli_accounts.Path, name)

        def watch(path, *arguments, _original=original, **options):
            touched.append(str(path))
            return _original(path, *arguments, **options)
        monkeypatch.setattr(cli_accounts.Path, name, watch)
    assert len(cli_accounts.found_accounts()) == 2
    inside = [path for path in touched for folder in ('.claude-account2', '.codex-work')
              if path.startswith(str(home / folder) + os.sep)]
    assert inside == []


def test_a_folder_found_only_by_name_is_listed_only_when_its_cli_says_it_is_signed_in(home, monkeypatch):
    (home / '.codex-cache').mkdir()
    (home / '.codex-work').mkdir()
    program(home / 'bin' / 'codex2.cmd', f'set CODEX_HOME={home}/.codex-2\ncodex %*\n')

    async def signed_in(account):
        return {**account, 'signed_in': account['account_dir'].endswith('.codex-work'), 'email': ''}
    monkeypatch.setattr(cli_accounts, 'signed_in', signed_in)
    accounts = asyncio.run(cli_accounts.accounts_with_logins())
    # The codex2 command is kept, signed in or not; of the folders only found by name, only the signed-in one.
    assert {account['account_dir'] for account in accounts} == {f'{home}/.codex-2', str(home / '.codex-work')}
    assert all('guess' not in account for account in accounts)


def test_the_scan_keeps_only_the_folder_from_a_start_up_file(home):
    program(home / '.bashrc', f'export OPENAI_API_KEY=sk-not-for-the-list\nalias codex2="CODEX_HOME={home}/.codex-2 codex"\n')
    accounts = cli_accounts.found_accounts()
    assert 'sk-not-for-the-list' not in repr(accounts)
    assert [account['account_dir'] for account in accounts] == [f'{home}/.codex-2']


def test_the_usual_folder_set_by_hand_is_the_usual_account(home):
    program(home / 'bin' / 'claude')
    program(home / 'bin' / 'claude.cmd')
    program(home / 'bin' / 'claude1.cmd', 'set CLAUDE_CONFIG_DIR=%USERPROFILE%/.claude\nclaude %*\n')
    [account] = cli_accounts.found_accounts()
    assert account['account_dir'] == '' and account['commands'] == ['claude', 'claude1']


@pytest.mark.skipif(os.name == 'nt', reason='the stand-in codex is a script with a #! line')
def test_the_list_says_which_accounts_are_signed_in(home):
    program(home / 'bin' / 'claude2.cmd', f'set CLAUDE_CONFIG_DIR={home}/.claude-2\nclaude %*\n')
    program(home / 'bin' / 'codex', f'#!{sys.executable}\nimport os, sys\n'
            f'sys.exit(0 if os.environ.get("CODEX_HOME") == {str(home / ".codex-2")!r} else 1)\n')
    program(home / 'bin' / 'codex2.cmd', f'set CODEX_HOME={home}/.codex-2\ncodex %*\n')
    accounts = asyncio.run(cli_accounts.accounts_with_logins())
    shown = {(account['provider'], account['account_dir']): account['signed_in'] for account in accounts}
    # No claude program at all: its wrapper is listed, not signed in. Codex answers for the second folder only.
    assert shown == {('claude_code', f'{home}/.claude-2'): False, ('codex', ''): False,
                     ('codex', f'{home}/.codex-2'): True}


def test_the_route_lists_the_accounts_unless_looking_is_turned_off(home, client):
    program(home / 'bin' / 'codex2.cmd', f'set CODEX_HOME={home}/.codex-2\ncodex %*\n')
    found = client.get('/api/models/cli-accounts').json()
    assert found['enabled'] is True
    assert [(account['provider'], account['commands']) for account in found['accounts']] == [('codex', ['codex2'])]
    assert client.put('/api/settings', json={'find_cli_accounts': False}).json()['find_cli_accounts'] is False
    assert client.get('/api/models/cli-accounts').json() == {'enabled': False, 'accounts': []}


def test_a_codex_profile_runs_with_its_own_account_folder(home):
    config = {'provider': 'codex', 'cli_account_dir': f'{home}/.codex-2'}
    assert codex.cli_environment(config)['CODEX_HOME'] == f'{home}/.codex-2'
    assert codex.cli_environment({'provider': 'codex'}) is None
    assert resource_for(config) == (f'codex-cli:{home}/.codex-2', 1)
    assert f'{home}/.codex-2' in codex.login_step(config)
    assert codex.executable_path({'cli_path': sys.executable}) == sys.executable
