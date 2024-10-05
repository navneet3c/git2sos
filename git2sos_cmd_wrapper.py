#!/bin/python3

## run sos commands from the input git-like commands.
## follow a proxy authoritarian system where most things
## are passed on as-it-is but any unknown response is flagged

import datetime
import json
import os
import random
import shutil
import string
import subprocess
import sys
import time

class bcolors:
    GRAY = '\033[90m' if sys.stdout.isatty() else ''
    RED = '\033[31m' if sys.stdout.isatty() else ''
    GREEN = '\033[32m' if sys.stdout.isatty() else ''
    YELLOW = '\033[33m' if sys.stdout.isatty() else ''
    BLUE = '\033[34m' if sys.stdout.isatty() else ''
    MAGENTA = '\033[35m' if sys.stdout.isatty() else ''
    CYAN = '\033[36m' if sys.stdout.isatty() else ''
    BOLD = '\033[1m' if sys.stdout.isatty() else ''
    UNDERLINE = '\033[4m' if sys.stdout.isatty() else ''
    ENDC = '\033[0m' if sys.stdout.isatty() else ''

class SOSWrapper:
    def __init__(self):
        self.cache_path = ''
        self.wa_data_file = 'wa_data.json'
        self.diff_tool = os.environ['GIT_DIFF_TOOL'] if 'GIT_DIFF_TOOL' in os.environ else 'tkdiff'
        self.ign_filelist = ['./.gutctags']

        self.commands = {
            '-h': self.help_myscript,
            'add': self.add_sos,            # not a sos feature
            #'blame': self.blame_sos,       # not a sos feature
            'checkout': self.checkout_sos,
            'cleanup': self.cleanup_sos,    # not a git command
            'clone': self.clone_sos,
            'declone': self.declone_sos,    # not a git command
            'diff': self.diff_sos,
            'discard': self.discard_sos,    # not a git command
            'fetch': self.fetch_sos,
            'help': self.help_sos,
            'log': self.log_sos,
            'merge': self.merge_sos,
            'mv': self.mv_sos,
            'pull': self.pull_sos,
            'push': self.push_sos,
            'rm': self.rm_sos,
            'stash': self.stash_sos,
            'status': self.status_sos,
            # Add more commands as needed
        }

    def help_myscript(self, args):
        print('''Script to translate (^_^) Git-like commands to SOS commands.
Adds few extra commands for ease-of-use.
Commands are Git-like, but extra args are SOS-like and passed on to SOS.
Few of the SOS commands which cause changes to files are printed as output.

Command arguments should be provided like '-argval' instead of '-arg val' so
that they can be properly skipped/identified.

List of possible usages:
  script.py add [<extra args ...>] <filename> <filename>
      Checkout a file from server for editing. In Git 'add' is done after
      editing a file. Here we must 'checkout' before editing a file. Any
      additional args given are passed to the checkout command of SOS.

      Creating a file is handled differently in SOS. This script detects all
      files listed for create and saves the state. Later when the push command
      is executed then the creation in SOS server is actually performed.

      If more control is needed then separate script call for create and edit
      can be done.

  script.py checkout '<YYYY/MM/DD> <HH:MM:SS>'
  script.py checkout <branch>
  script.py checkout <label/tag> <label/tag>
      Change the RSO to new branch/tag/label.
      If time is provided as input, update workarea to given time.

  script.py cleanup
      Clean up the workarea. Removes all unmanaged files and updates workspace
      with consistency checks enabled.

      This is similar to Git hard reset and clean.

  script.py clone <workarea_path>
  script.py clone <server> <project> <workarea_path> [<extra args ...>]
      Creates a new workarea in workarea_path. SOS cached mode is enabled.
      If only the path is provided, then project/server names are taken
      from the environment.

  script.py declone [<extra args ...>]
      Deletes a workarea from SOS server's records. A SOS workarea should not
      be deleted without this step.
      After running this command the workspace directory should be manually
      removed.

  script.py diff
  script.py diff '<YYYY/MM/DD> <HH:MM:SS>'
  script.py diff -r<rev> -r<rev> <filename>
  script.py diff <filename> <filename>
      Shows diff of current changes.
      If no argument is passed, shows diff of all files checked-out.
      If time is provided as input, then shows diff for the change(s) at given time.
      If a filename and two revisions are provided with -r argument, then the diff
      between the given versions of the file is shown.
      If some file names are passed, then shows diff for those files.

      This is similar to Git diff/difftool.

  script.py discard [<extra args ...>] <filename> <filename>
      Discards checkout or any delete/move/add records for the given files.
      Any extra args are passed to the discardco SOS command.
      Works similar to the Git reset HEAD.

  script.py fetch [<extra args ...>]
      Retrieves new file info from server but does not update.

  script.py help
  script.py help [<extra args ...>]
      Shows help info from SOS.

  script.py log [<extra args ...>]
  script.py log '<YYYY/MM/DD> <HH:MM:SS>'
  script.py log <filename> <filename> [<extra args ...>]
      Shows history of file or project. By default shows log of last 5
      days and lists all file change/modification activities.

      If no filename is given, then shows history of project.
      If only time is given, then shows the revision(s) for that time.
      If filename is given then shows history of the file.

      Extra args are passed on to SOS if applicable.
      e.g. -from-7 shows log from last 7 days.
      e.g. -userprojeng shows log only from user 'projeng'.

  script.py merge
      Feature TBD

  script.py mv <filename> <filename> <target>
      Saves the state of the given files to move to the target directory.
      Later when the push command is executed then the move in SOS server
      is actually performed.

      If a file is moved multiple times, only the latest move is recorded.
      No file validity checks are done and it is assumed that the SOS command
      will error out if invalid paths are provided.

  script.py pull [<extra args ...>]
      Updates the workspace with changes from server.

  script.py push
      Submits the changes in current workspace to the server.
      The list of changed files is shown to the user for review and getting
      the change description. The changes are then sent to server in the order
      of check-in, delete, move and then create.
      The script's internal cache state is also updated.

  script.py rm <filename> <filename>
      Saves the state of the given files for delete. Later when the push
      command is executed then the deletion in SOS server is actually
      performed.

      No file validity checks are done and it is assumed that the SOS command
      will error out if invalid paths are provided.

  script.py stash
  script.py stash create  <description>
  script.py stash list
  script.py stash preview <stash_id>
  script.py stash apply   [<stash_id>]
  script.py stash drop    <stash_id> <stash_id>
      Manages a stash with all local changes and script-cache data. The stash
      is created in user's home directory.

      Passing no argument acts as stash create.
      Arguments passed while creating stash are used as stash description.
      The current status of files is used to create the stash.

      For preview, the given stash_id is previewed without changing any local
      files.

      For apply, the given stash_id is applied to the current workspace. If
      no stash_id is given, then the latest stash is used.

      For drop, the given stash_id are deleted. If no argument is given, then
      the latest stash is dropped.

  script.py status
  script.py status <path> <path>
  script.py status [<extra args ...>] <path> <path>
      Prints the status of current workspace.
      If file names or paths are provided, then shows status within those
      scope.

      The files which are checked out, untracked or listed for
      create/delete/move are listed. Any args are passed to the SOS command to
      list files.

Bye.''')

    def add_sos(self, args):
        self.check_args_count(args, min=1)
        self.setup_user_cache()
        wa_data_file_path = os.path.join(self.cache_path, self.wa_data_file)
        wa_data = {}

        if os.path.isfile(wa_data_file_path) and os.path.getsize(wa_data_file_path):
            with open(wa_data_file_path, 'r') as cache_file:
                wa_data = json.load(cache_file)
        wa_root = self.get_wa_root_path()
        self.init_json_hier(wa_data, list, ['file_status', 'create'])

        new_args = []
        for arg in args:
            if arg.startswith('-'):
                new_args.append(arg)
                continue

            obj_status = self.execute_sos_command(['soscmd', 'objstatus'], [arg], ret_text=True, quiet=True)
            obj_status = obj_status[0].split() if len(obj_status) == 1 else []
            if len(obj_status) != 2: # cmd returns file status and type
                print(f'Skipping \'{arg}\' because stat returned unexpected status.')

            if obj_status[0] in ['2']: # unmanaged file
                rel_path = os.path.relpath(arg, wa_root)
                if rel_path not in wa_data['file_status']['create']:
                    wa_data['file_status']['create'].append(rel_path)
                    print(f'Adding \'{arg}\' for create.')
                else:
                    print(f'Skipping \'{arg}\' for create as it is already listed.')
            elif obj_status[0] in ['3', '6']: # already checked out
                print(f'Skipping \'{arg}\' because it is already checked out.')
            elif obj_status[0] in ['4', '5']: # valid path checked-in
                new_args.append(arg)
                print(f'Adding \'{arg}\' for checkout.')
            else: # including 0 [file not part of workarea] and 1 [does not exist]
                print(f'Skipping \'{arg}\' as the file is not valid.')

        # save file status data
        with open(wa_data_file_path, 'w') as cache_file:
            json.dump(wa_data, cache_file, indent=2)

        if new_args:
            self.execute_sos_command(['soscmd', 'co'], ['-C'] + new_args)

    def checkout_sos(self, args):
        branches = self.execute_sos_command(['soscmd', 'query'], ['branches'], ret_text=True, quiet=True)
        if len(args) == 1 and args[0] in branches:
            self.execute_sos_command(['soscmd', 'usebranch'], args)
            return
        if len(args) == 1 and args[0][:1].isdigit():
            datetime_object = self.get_datetime_from_str(args[0])
            if datetime_object:
                self.execute_sos_command(['soscmd', 'update'], [f'-t{args[0]}'])
                return
        self.check_args_count(args, min=1)
        new_args = [f'-l{arg}' for arg in args]
        self.execute_sos_command(['soscmd', 'update'], ['-rso'] + new_args)

    def cleanup_sos(self, args):
        self.check_args_count(args, max=0)

        # remove untracked files
        print('Waiting for 5 seconds.')
        print(f'{bcolors.RED}All untracked files will be deleted.{bcolors.ENDC}')
        time.sleep(5)
        wa_root = self.get_wa_root_path()
        unm_filelist = self.execute_sos_command(['soscmd', 'status'], ['-f%P', '-sunm'], ret_text=True, quiet=True)
        for file_path in unm_filelist:
            if file_path.startswith('*') or file_path in self.ign_filelist:
                continue
            print(f'Removing file #\'{file_path}\'.')
            file_path = os.path.join(wa_root, file_path)
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                os.rmdir(file_path)

        # update workspace
        self.execute_sos_command(['soscmd', 'update'], ['-ccw'] + args)

    def clone_sos(self, args):
        if len(args) == 1:
            self.execute_sos_command(['soscmd', 'newworkarea'], [os.environ['SOS_SERVER'], os.environ['SOS_PROJECT'], args[0], '-LCACHED'])
        elif len(args) >= 3:
            self.execute_sos_command(['soscmd', 'newworkarea'], [args.pop(0), args.pop(0), args.pop(0), '-LCACHED'] + args)
        else:
            print(f'{bcolors.RED}Error: Invalid args. Enter args after command: <server> <project> <path> <extra args ...>{bcolors.ENDC}')
            exit(1)

    def declone_sos(self, args):
        self.check_args_count(args, max=0)
        print('Waiting for 5 seconds.')
        print(f'{bcolors.RED}The workspace will be deleted.{bcolors.ENDC}')
        time.sleep(5)

        self.execute_sos_command(['soscmd', 'deleteworkarea'], ['-F'] + args)

    def diff_sos(self, args):
        co_filelist = []
        wa_root = self.get_wa_root_path()
        get_co_files = False
        try:
            if not len(args):
                raise Exception()
            if len(args) == 3 and args[0].startswith('-r') and args[1].startswith('-r') and os.path.exists(args[2]):
                rev1 = self.remove_prefix(args[0], '-r')
                rev2 = self.remove_prefix(args[1], '-r')
                co_filelist.append(f'{args[2]} {rev1} {rev2}')
            elif len(args) == 1 and args[0][:1].isdigit():
                datetime_object = self.get_datetime_from_str(args[0])
                if not datetime_object:
                    raise Exception()
                adj_from_datetime, adj_to_datetime = self.adjust_datetime_war(datetime_object)
                log_data = self.execute_sos_command(['soscmd', 'audit'], ['-f%date %user %cmd %obj %rev %summary', '-sfo', '-group', '-cmdci', f'-from{adj_from_datetime}', f'-to{adj_to_datetime}'], ret_text=True, quiet=True)
                for line in log_data:
                    if line[:1].isdigit():
                        line = line.split()
                        print(f'Found change at \'{line[0]} {line[1]}\' from \'{line[2]}\': \'{" ".join(line[5:])}\'')
                    elif line.startswith(' '):
                        line = line.split()
                        rel_filepath = os.path.relpath(os.path.join(wa_root, line[4]), os.getcwd())
                        prev_rev = int(line[5]) - 1 if int(line[5]) > 1 else 1
                        co_filelist.append(f'{rel_filepath} {prev_rev} {line[5]}')
            else:
                raise Exception()
        except Exception as e:
            get_co_files = True
        if get_co_files:
            co_filelist = self.execute_sos_command(['soscmd', 'status'], ['-f%P', '-sco'] + args, ret_text=True, quiet=True)
            co_filelist = [os.path.relpath(os.path.join(wa_root, file), os.getcwd()) for file in co_filelist if not file.startswith('*')]

        for file_data in co_filelist:
            file_data = file_data.split() # has file path and revisions
            file_path = file_data[0]
            if os.path.isdir(file_path):
                print(f'Skipping \'{file_path}\' as it is a directory.')
                continue
            file_name = os.path.basename(file_path)

            tmp_filepath1, tmp_filepath2 = ('',) * 2
            print(f'Diff for \'{file_path}\'.')
            if len(file_data) > 2:
                tmp_filepath1 = self.generate_temp_filename() + f'__{file_name}.{file_data[1]}'
                tmp_filepath2 = self.generate_temp_filename() + f'__{file_name}.{file_data[2]}'
                self.execute_sos_command(['soscmd', 'exportrev'], [f'{file_path}/{file_data[1]}', f'-out{tmp_filepath1}'], quiet=True)
                self.execute_sos_command(['soscmd', 'exportrev'], [f'{file_path}/{file_data[2]}', f'-out{tmp_filepath2}'], quiet=True)
            else:
                tmp_filepath1 = self.generate_temp_filename() + f'__{file_name}'
                tmp_filepath2 = file_path
                self.execute_sos_command(['soscmd', 'exportrev'], [file_path, f'-out{tmp_filepath1}'], quiet=True)
            subprocess.call([self.diff_tool, tmp_filepath1, tmp_filepath2], stdout=subprocess.DEVNULL)
            os.remove(tmp_filepath1)
            if len(file_data) > 2:
                os.remove(tmp_filepath2)

    def discard_sos(self, args):
        self.check_args_count(args, min=1)
        self.setup_user_cache()
        wa_data_file_path = os.path.join(self.cache_path, self.wa_data_file)
        wa_data = {}

        if os.path.isfile(wa_data_file_path) and os.path.getsize(wa_data_file_path):
            with open(wa_data_file_path, 'r') as cache_file:
                wa_data = json.load(cache_file)
        wa_root = self.get_wa_root_path()
        self.init_json_hier(wa_data, dict, ['file_status'])

        new_args = []
        new_dir_args = []
        paths_to_remove = []
        for arg in args:
            if arg.startswith('-'):
                new_args.append(arg)
                continue

            obj_status = self.execute_sos_command(['soscmd', 'objstatus'], [arg], ret_text=True, quiet=True)
            obj_status = obj_status[0].split() if len(obj_status) == 1 else []
            if len(obj_status) != 2: # cmd returns file status and type
                print(f'Skipping \'{arg}\' because stat returned unexpected status.')

            if obj_status[1] in ['2']: # add directory
                if not new_dir_args:
                    new_dir_args = ['-sr', '-sco']
                new_args.append(arg)
                print(f'Adding directory \'{arg}\' for discarding checkout.')
            elif obj_status[0] in ['3', '6']: # unmanaged file
                new_args.append(arg)
                print(f'Adding \'{arg}\' for discarding checkout.')

            rel_path = os.path.relpath(arg, wa_root)
            if os.path.isdir(rel_path):
                rel_path += '/'
            paths_to_remove.append(rel_path)

        # clean up the local file status
        for key in ['create', 'delete']:
            if key not in wa_data['file_status']:
                continue
            for file in wa_data['file_status'][key]:
                if file.startswith(tuple(paths_to_remove)):
                    print(f'Removing #\'{file}\' from {key} list.')
                    wa_data['file_status'][key].remove(file)
        for key in ['move']: # live with the 5 level nest below
            if key not in wa_data['file_status']:
                continue
            for subpath in wa_data['file_status'][key]:
                for file in wa_data['file_status'][key][subpath]:
                    if file.startswith(tuple(paths_to_remove)):
                        print(f'Removing #\'{file}\' from {key} list.')
                        wa_data['file_status'][key][subpath].remove(file)

        # save file status data
        with open(wa_data_file_path, 'w') as cache_file:
            json.dump(wa_data, cache_file, indent=2)

        if new_args:
            self.execute_sos_command(['soscmd', 'discardco'], ['-F'] + new_dir_args + new_args)

    def fetch_sos(self, args):
        self.execute_sos_command(['soscmd', 'update'], ['-i', '-pr'] + args)

    def help_sos(self, args):
        self.execute_sos_command(['soscmd', 'help'], args)

    def log_sos(self, args):
        user_set_arg_cmd, user_set_arg_from = (False,) * 2
        new_args = []
        for idx, arg in enumerate(args):
            if arg.startswith('-cmd'):
                user_set_arg_cmd = True
                new_args.append(arg)
            elif arg.startswith('-from'):
                user_set_arg_from = True
                new_args.append(arg)
            elif arg[:1].isdigit() and not user_set_arg_from:
                datetime_object = self.get_datetime_from_str(arg)
                if not datetime_object: # skip if cannot get date
                    new_args.append(arg)
                    continue

                user_set_arg_from = True
                adj_from_datetime, adj_to_datetime = self.adjust_datetime_war(datetime_object)
                new_args.extend([f'-from{adj_from_datetime}', f'-to{adj_to_datetime}'])
            else:
                new_args.append(arg)
        args = new_args

        if not user_set_arg_cmd:
            args[:0] = ['-cmdcreate', '-cmdci', '-cmddelete', '-cmdrename', '-cmdmerge', '-cmdmove']
        if not user_set_arg_from:
            args[:0] = ['-from-5']
        log_data = self.execute_sos_command(['soscmd', 'audit'], ['-f%date %user %cmd %obj %rev %summary', '-sfo', '-group'] + args, ret_text=True, quiet=True)

        log_text = ''
        for line in log_data:
            if line[:1].isdigit():
                line = line.split()
                if log_text:
                    log_text += f'\n'
                log_text += f'{bcolors.YELLOW}Date:    {line[0]} {line[1]} {"-"*30}{bcolors.ENDC}\n'
                log_text += f'Log:     {" ".join(line[5:])}\n'
                log_text += f'Author:  {line[2]}\n'
                log_text += f'Files:\n'
            elif line.startswith(' '):
                line = line.split()
                log_text += f'... {line[3]:10} {line[4]}/{line[5]}\n'
        if sys.stdout.isatty():
            tmp_filepath = self.generate_temp_filename()
            with open(tmp_filepath, 'w') as tmp_file:
                tmp_file.write(log_text)
            subprocess.call(['less', '-R', tmp_filepath])
            os.remove(tmp_filepath)
        else:
            print(log_text, end='')

    def merge_sos(self, args):
        print(f'Feature TBD')

    def mv_sos(self, args):
        self.check_args_count(args, min=2)
        self.setup_user_cache()
        wa_data_file_path = os.path.join(self.cache_path, self.wa_data_file)
        wa_data = {}

        if os.path.isfile(wa_data_file_path) and os.path.getsize(wa_data_file_path):
            with open(wa_data_file_path, 'r') as cache_file:
                wa_data = json.load(cache_file)
        wa_root = self.get_wa_root_path()
        target_dir = os.path.relpath(args.pop(), wa_root)
        self.init_json_hier(wa_data, list, ['file_status', 'move', target_dir])

        for arg in args:
            rel_path = os.path.relpath(arg, wa_root)
            if rel_path not in wa_data['file_status']['move'][target_dir]:
                # remove this path from all other records
                for target_dir_tmp in wa_data['file_status']['move']:
                    if rel_path in wa_data['file_status']['move'][target_dir_tmp]:
                        wa_data['file_status']['move'][target_dir_tmp].remove(rel_path)
                wa_data['file_status']['move'][target_dir].append(rel_path)
                print(f'Adding \'{arg}\' for move to #\'./{target_dir}\'.')
            else:
                print(f'Skipping \'{arg}\' for move as it is already listed.')

        # save file status data
        with open(wa_data_file_path, 'w') as cache_file:
            json.dump(wa_data, cache_file, indent=2)

    def pull_sos(self, args):
        self.execute_sos_command(['soscmd', 'update'], args)

    def push_sos(self, args):
        # prepare data structures
        self.setup_user_cache()
        wa_data_file_path = os.path.join(self.cache_path, self.wa_data_file)
        wa_data = {}

        if os.path.isfile(wa_data_file_path) and os.path.getsize(wa_data_file_path):
            with open(wa_data_file_path, 'r') as cache_file:
                wa_data = json.load(cache_file)
        wa_root = self.get_wa_root_path()
        self.init_json_hier(wa_data, dict, ['file_status'])

        ## prepare check-in
        tmp_filepath = self.generate_temp_filename()
        self.push_prepare(args, wa_root, wa_data, tmp_filepath)

        # get description from user
        subprocess.call(['vi', tmp_filepath])

        #process user's data
        self.push_action(args, wa_root, wa_data, tmp_filepath)

        # save file status data
        with open(wa_data_file_path, 'w') as cache_file:
            json.dump(wa_data, cache_file, indent=2)

    def push_prepare(self, args, wa_root, wa_data, tmp_filepath):
        commit_text  = '''

#
# Enter change description above. Lines starting with '#' will
# be ignored, and an empty message aborts the commit.
#
# The files for commit operations are listed below. Below files
# or sections may be removed to exclude them.
# The section headers must not be edited.
#
#
'''
        cur_filelist = self.execute_sos_command(['soscmd', 'status'], ['-f%P', '-sco'], ret_text=True, quiet=True)
        sel_filelist = []
        for file in cur_filelist:
            if file.startswith('*'):
                continue
            file = os.path.relpath(os.path.join(wa_root, file), os.getcwd())
            sel_filelist.append(file)
        if sel_filelist:
            print('Adding files for check-in.')
            commit_text += '# Files for check-in:\n'
            for file in sel_filelist:
                commit_text += f'#    ./{file}\n'
            commit_text += '#\n'

        ## prepare delete
        sel_filelist = []
        if 'delete' in wa_data['file_status']:
            for file in wa_data['file_status']['delete']:
                file = os.path.relpath(os.path.join(wa_root, file), os.getcwd())
                sel_filelist.append(file)
        if sel_filelist:
            print('Adding files for delete.')
            commit_text += '# Files for delete:\n'
            for file in sel_filelist:
                commit_text += f'#    ./{file}\n'
            commit_text += '#\n'

        ## prepare move
        sel_filelist = {}
        if 'move' in wa_data['file_status']:
            for target_dir in wa_data['file_status']['move']:
                target_relpath = os.path.relpath(os.path.join(wa_root, target_dir), os.getcwd())
                if not len(wa_data['file_status']['move'][target_dir]):
                    continue
                sel_filelist[target_relpath] = []
                for file in wa_data['file_status']['move'][target_dir]:
                    file = os.path.relpath(os.path.join(wa_root, file), os.getcwd())
                    sel_filelist[target_relpath].append(file)
        if sel_filelist:
            print('Adding files for move.')
            commit_text += '# Files for move:\n'
            for target_dir in sel_filelist:
                commit_text += f'#    Move to ./{target_dir}\n'
                for file in sel_filelist[target_dir]:
                    commit_text += f'#        ./{file}\n'
            commit_text += '#\n'

        ## prepare create
        sel_filelist = []
        if 'create' in wa_data['file_status']:
            for file in wa_data['file_status']['create']:
                file = os.path.relpath(os.path.join(wa_root, file), os.getcwd())
                sel_filelist.append(file)
        if sel_filelist:
            print('Adding files for create.')
            commit_text += '# Files for create:\n'
            for file in sel_filelist:
                commit_text += f'#    ./{file}\n'
            commit_text += '#\n'

        with open(tmp_filepath, 'w') as tmp_file:
            tmp_file.write(commit_text)

    def push_action(self, args, wa_root, wa_data, tmp_filepath):
        user_desc = []
        sel_filelist = {'checkin': [], 'delete': [], 'move': {}, 'create': []}
        with open(tmp_filepath, 'r') as tmp_file:
            list_mode = ''
            move_tgt_dir = ''
            for line in tmp_file:
                line = line.strip()
                if line and line[0] == '#':
                    if line == '#':
                        list_mode = ''
                    elif list_mode in ['checkin', 'delete', 'create']:
                        sel_filelist[list_mode].append(line[1:].strip())
                    elif list_mode == 'move':
                        if line.startswith('#    Move to '):
                            line = self.remove_prefix(line, '#    Move to ')
                            move_tgt_dir = line.strip()
                            sel_filelist[list_mode][move_tgt_dir] = []
                        else:
                            sel_filelist[list_mode][move_tgt_dir].append(line[1:].strip())
                    else:
                        if   line.startswith('# Files for check-in:'):
                            list_mode = 'checkin'
                        elif line.startswith('# Files for delete:'):
                            list_mode = 'delete'
                        elif line.startswith('# Files for move:'):
                            list_mode = 'move'
                        elif line.startswith('# Files for create:'):
                            list_mode = 'create'
                else:
                    if line or user_desc: # avoid blank lines before description
                        user_desc.append(line)
        os.remove(tmp_filepath)
        while user_desc and not user_desc[-1]: # remove blank lines after description
            user_desc.pop()
        if not user_desc:
            print(f'{bcolors.RED}No description provided. Aborting.{bcolors.ENDC}')
            exit(1)
        user_desc = '\n'.join(user_desc)

        # process operations and commit files
        if sel_filelist['checkin']:
            self.execute_sos_command(['soscmd', 'ci'], ['-D', f'-aLog={user_desc}'] + sel_filelist['checkin'])
        if sel_filelist['delete']:
            self.execute_sos_command(['soscmd', 'delete'], sel_filelist['delete'])
            for file in sel_filelist['delete']:
                file = os.path.relpath(file, wa_root)
                if file in wa_data['file_status']['delete']:
                    wa_data['file_status']['delete'].remove(file)
        if sel_filelist['move']:
            for tgt_dir in sel_filelist['move']:
                co_dir_list = [tgt_dir]
                for file in sel_filelist['move'][tgt_dir]:
                    dir_of_file = os.path.dirname(file)
                    if dir_of_file not in co_dir_list:
                        co_dir_list.append(dir_of_file)
                self.execute_sos_command(['soscmd', 'co'], ['-C'] + co_dir_list)
                self.execute_sos_command(['soscmd', 'move'], sel_filelist['move'][tgt_dir] + [tgt_dir])
                for file in sel_filelist['move'][tgt_dir]:
                    file = os.path.relpath(file, wa_root)
                    tgt_dir_rel = os.path.relpath(tgt_dir, wa_root)
                    if file in wa_data['file_status']['move'][tgt_dir_rel]:
                        wa_data['file_status']['move'][tgt_dir_rel].remove(file)
        if 'move' in wa_data['file_status']:
            rem_list = []
            for tgt_dir in wa_data['file_status']['move']:
                if not wa_data['file_status']['move'][tgt_dir]:
                    rem_list.append(tgt_dir)
            for tgt_dir in rem_list:
                del wa_data['file_status']['move'][tgt_dir]
        if sel_filelist['create']:
            self.execute_sos_command(['soscmd', 'create'], [f'-aDescription={user_desc}'] + sel_filelist['create'])
            for file in sel_filelist['create']:
                file = os.path.relpath(file, wa_root)
                if file in wa_data['file_status']['create']:
                    wa_data['file_status']['create'].remove(file)

    def rm_sos(self, args):
        self.check_args_count(args, min=1)
        self.setup_user_cache()
        wa_data_file_path = os.path.join(self.cache_path, self.wa_data_file)
        wa_data = {}

        if os.path.isfile(wa_data_file_path) and os.path.getsize(wa_data_file_path):
            with open(wa_data_file_path, 'r') as cache_file:
                wa_data = json.load(cache_file)
        wa_root = self.get_wa_root_path()
        self.init_json_hier(wa_data, list, ['file_status', 'delete'])

        for arg in args:
            rel_path = os.path.relpath(arg, wa_root)
            if rel_path not in wa_data['file_status']['delete']:
                wa_data['file_status']['delete'].append(rel_path)
                print(f'Adding \'{arg}\' for delete.')
            else:
                print(f'Skipping \'{arg}\' for delete as it is already listed.')

        # save file status data
        with open(wa_data_file_path, 'w') as cache_file:
            json.dump(wa_data, cache_file, indent=2)

    def stash_sos(self, args):
        if len(args):
            if args[0] == 'list':
                self.stash_list(args[1:])
            elif args[0] == 'preview':
                self.stash_apply(args[1:], apply=False)
            elif args[0] == 'apply':
                self.stash_apply(args[1:])
            elif args[0] == 'drop':
                self.stash_drop(args[1:])
            elif args[0] == 'create':
                self.stash_create(args[1:])
            else:
                print(f'{bcolors.RED}Error: Unsupported stash command.{bcolors.ENDC}')
        else:
            self.stash_create(args[1:])

    def stash_create(self, args):
        self.setup_user_cache()
        wa_data_file_path = os.path.join(self.cache_path, self.wa_data_file)
        wa_data = {}

        if os.path.isfile(wa_data_file_path) and os.path.getsize(wa_data_file_path):
            with open(wa_data_file_path, 'r') as cache_file:
                wa_data = json.load(cache_file)
        wa_root = self.get_wa_root_path()
        self.init_json_hier(wa_data, dict, ['file_status'])

        stash_file_name = f'stash_{os.environ["USER"]}_' + self.generate_temp_filename(only_randstr=True)
        stash_file_path = os.path.join(self.cache_path, stash_file_name)
        stash_txt  = f'# info Name         : {stash_file_name}\n'
        stash_txt += f'# info Description  : {" ".join(args)}\n'
        stash_txt += f'# info Created      : {datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")}\n'
        # update stash_list if changing above

        # process checked out files
        co_filelist = self.execute_sos_command(['soscmd', 'status'], ['-f%V %P', '-sco'], ret_text=True, quiet=True)
        for file_data in co_filelist:
            if file_data.startswith('*'):
                continue
            file_data = file_data.split()
            file_rev = file_data[0]
            file_path = file_data[1]
            file_relpath = os.path.relpath(os.path.join(wa_root, file_path), os.getcwd())
            tmp_filepath = self.generate_temp_filename()
            self.execute_sos_command(['soscmd', 'exportrev'], [file_relpath, f'-out{tmp_filepath}'], quiet=True)
            diff_data = self.execute_sos_command(['diff'], ['-au', tmp_filepath, file_relpath], ret_text=True, chk_err=False, quiet=True)
            os.remove(tmp_filepath)
            stash_txt += f'# checkout ./{file_path} {file_rev}\n'
            stash_txt += '\n'.join(diff_data)
            stash_txt += '\n'
            print(f'  {bcolors.BLUE}[checkout ]{bcolors.ENDC} \'{file_path}\'')

        #process cached data of files
        if 'create' in wa_data['file_status']:
            for file_path in wa_data['file_status']['create']:
                file_relpath = os.path.relpath(os.path.join(wa_root, file_path), os.getcwd())
                with open(file_relpath, 'r') as cr_file:
                    file_text = cr_file.read()
                    line_count = file_text.count('\n')
                    stash_txt += f'# create ./{file_path} {line_count}\n'
                    stash_txt += file_text
                    print(f'  {bcolors.BLUE}[create   ]{bcolors.ENDC} \'./{file_path}\'')
        if 'delete' in wa_data['file_status']:
            for file_path in wa_data['file_status']['delete']:
                stash_txt += f'# delete ./{file_path}\n'
                print(f'  {bcolors.BLUE}[delete   ]{bcolors.ENDC} \'./{file_path}\'')
        if 'move' in wa_data['file_status']:
            for tgt_dir in wa_data['file_status']['move']:
                for file_path in wa_data['file_status']['move'][tgt_dir]:
                    stash_txt += f'# move ./{file_path} ./{tgt_dir}\n'
                    print(f'  {bcolors.BLUE}[move     ]{bcolors.ENDC} \'./{file_path}\'')
        stash_txt += f'# info Marker : End of stash\n'

        # save the stash data
        with open(stash_file_path, 'w') as tmp_file:
            tmp_file.write(stash_txt)
            print(f'Created stash \'{stash_file_name}\'')

    def stash_list(self, args):
        self.setup_user_cache()
        cache_files = os.listdir(self.cache_path)
        stash_names_list = []
        for file_name in cache_files:
            file_path = os.path.join(self.cache_path, file_name)
            if not os.path.isfile(file_path) or not file_name.startswith('stash_'):
                continue
            stash_time, stash_desc = ('',) * 2
            with open(file_path) as stash_file:
                for line in stash_file:
                    if not line.startswith('#'):
                        break
                    if line.startswith('# info Created '):
                        stash_time = ' '.join(line.split()[4:])
                    elif line.startswith('# info Description '):
                        stash_desc = ' '.join(line.split()[4:])
            stash_names_list.append(f'{bcolors.BLUE}[{stash_time}]{bcolors.ENDC} {file_name} {bcolors.YELLOW}{stash_desc}{bcolors.ENDC}')
        stash_names_list.sort(reverse=True)
        for name in stash_names_list:
            print(name)

    def stash_apply(self, args, apply=True):
        stash_path = None
        user_cache_setup_done = False

        # get stash name from args
        if apply:
            self.check_args_count(args, min=0, max=1)
            if args:
                stash_path = args[0]
            else:
                self.setup_user_cache()
                user_cache_setup_done = True
                stash_path = self.get_latest_stash_name()
        else:
            self.check_args_count(args, min=1, max=1)
            stash_path = args[0]

        # check stash name
        if stash_path:
            try:
                name_parts = stash_path.split('_')
                if len(name_parts) != 3 or name_parts[0] != 'stash':
                    raise Exception(f'Invalid stash name: {stash_path}')
                if not user_cache_setup_done:
                    self.setup_user_cache(name_parts[1])
                stash_path = os.path.join(self.cache_path, stash_path)
                if not os.path.isfile(stash_path):
                    raise Exception(f'Invalid stash file: {stash_path}')
            except Exception as e:
                print(f'{bcolors.RED}Error in checking stash name: {e}{bcolors.ENDC}')
                stash_path = None
        if not stash_path:
            print(f'{bcolors.RED}Error: No valid stash to use.{bcolors.ENDC}')
            exit(1)

        # process the stash
        wa_root = self.get_wa_root_path()
        pop_has_error = False # may use this for cleanup
        with open(stash_path) as stash_file:
            ctx_data = {}
            txt_counter = 0
            for line in stash_file:
                if not txt_counter and line.startswith('#'):
                    # process previous command
                    if ctx_data:
                        self.stash_pop_process(ctx_data)
                        if ctx_data['has_error']:
                            pop_has_error = True

                    # start next command
                    line_parts = line.strip().split()
                    if len(line_parts) < 3:
                        print(f'{bcolors.RED}Unexpected line: {line}{bcolors.ENDC}')
                        exit(1)
                    ctx_data = {
                        'mode': line_parts[1],
                        'file': line_parts[2],
                        'txt': '',
                        'wa_root': wa_root,
                        'apply': apply,
                        'has_error': False
                    }
                    if line_parts[1] == 'info':
                        ctx_data['info'] = ' '.join(line_parts[4:])
                    elif line_parts[1] == 'checkout':
                        ctx_data['rev'] = line_parts[3]
                    elif line_parts[1] == 'create':
                        ctx_data['count'] = line_parts[3]
                        txt_counter = int(ctx_data['count'])
                    elif line_parts[1] == 'move':
                        ctx_data['tgt'] = line_parts[3]
                else:
                    ctx_data['txt'] += line
                    if txt_counter > 0:
                        txt_counter -= 1

    def stash_pop_process(self, ctx_data):
        if   ctx_data['mode'] == 'info':
            print(f'{bcolors.YELLOW}{ctx_data["file"]:15} : {ctx_data["info"]}{bcolors.ENDC}')
        elif ctx_data['mode'] == 'checkout':
            patch_args = ['--merge', '-uNt']
            if ctx_data['apply']:
                dest_file_path = os.path.relpath(os.path.join(ctx_data['wa_root'], ctx_data['file']), os.getcwd())
                if not os.path.exists(dest_file_path):
                    print(f'Skipping checkout for #\'{ctx_data["file"]}\' as it does not exist.')
                    return
                self.add_sos([dest_file_path]) # make file writable

                diff_file_path = self.generate_temp_filename()
                with open(diff_file_path, 'w') as tmp_file:
                    tmp_file.write(ctx_data['txt'])
                ret_code = self.execute_sos_command(['patch'], patch_args + [dest_file_path, diff_file_path], ret_code=True, chk_err=False, quiet=True)
                os.remove(diff_file_path)
                if ret_code:
                    print(f'Merged #\'{ctx_data["file"]}\' with error(s).')
                    ctx_data['has_error'] = True
                else:
                    print(f'Merged changes in #\'{ctx_data["file"]}\'.')
            else:
                file_name = os.path.basename(ctx_data['file'])
                dest_relpath = os.path.relpath(os.path.join(ctx_data['wa_root'], ctx_data['file']), os.getcwd())

                tmp_ref_file_path = self.generate_temp_filename() + f'__{file_name}.{ctx_data["rev"]}'
                dest_file_path = self.generate_temp_filename() + f'__{file_name}'
                self.execute_sos_command(['soscmd', 'exportrev'], [f'{dest_relpath}/#/{ctx_data["rev"]}', f'-out{tmp_ref_file_path}'], quiet=True)
                shutil.copyfile(tmp_ref_file_path, dest_file_path)

                diff_file_path = self.generate_temp_filename()
                with open(diff_file_path, 'w') as tmp_file:
                    tmp_file.write(ctx_data['txt'])
                ret_code = self.execute_sos_command(['patch'], patch_args + [dest_file_path, diff_file_path], ret_code=True, quiet=True)
                os.remove(diff_file_path)

                print(f'Preview #\'{ctx_data["file"]}\' for edit.')
                subprocess.call([self.diff_tool, tmp_ref_file_path, dest_file_path], stdout=subprocess.DEVNULL)
                os.remove(tmp_ref_file_path)
                os.remove(dest_file_path)
        elif ctx_data['mode'] == 'create':
            if ctx_data['apply']:
                dest_file_path = os.path.relpath(os.path.join(ctx_data['wa_root'], ctx_data['file']), os.getcwd())
                if os.path.exists(dest_file_path):
                    print(f'Skipping create for #\'{ctx_data["file"]}\' as it already exists.')
                    return
                with open(dest_file_path, 'w') as tmp_file:
                    tmp_file.write(ctx_data['txt'])
                self.add_sos([dest_file_path])
            else:
                file_name = os.path.basename(ctx_data['file'])
                dest_file_path = self.generate_temp_filename() + f'__{file_name}'
                with open(dest_file_path, 'w') as tmp_file:
                    tmp_file.write(ctx_data['txt'])
                print(f'Preview #\'{ctx_data["file"]}\' for create.')
                subprocess.call([self.diff_tool, dest_file_path, dest_file_path], stdout=subprocess.DEVNULL)
                os.remove(dest_file_path)
        elif ctx_data['mode'] == 'delete':
            if ctx_data['apply']:
                file_relpath = os.path.relpath(os.path.join(ctx_data['wa_root'], ctx_data['file']), os.getcwd())
                self.rm_sos([file_relpath])
            else:
                print(f'Skipping delete for #\'{ctx_data["file"]}\'.')
        elif ctx_data['mode'] == 'move':
            if ctx_data['apply']:
                file_relpath = os.path.relpath(os.path.join(ctx_data['wa_root'], ctx_data['file']), os.getcwd())
                tgt_relpath = os.path.relpath(os.path.join(ctx_data['wa_root'], ctx_data['tgt']), os.getcwd())
                self.mv_sos([file_relpath, tgt_relpath])
            else:
                print(f'Skipping move for #\'{ctx_data["file"]}\'.')

    def stash_drop(self, args):
        self.setup_user_cache()

        stash_to_delete = []
        if args:
            for file_name in args:
                file_path = os.path.join(self.cache_path, file_name)
                if os.path.isfile(file_path) and file_name.startswith('stash_'):
                    stash_to_delete.append(file_name)
        else:
            latest_stash_name = self.get_latest_stash_name()
            if latest_stash_name:
                stash_to_delete.append(latest_stash_name)

        if not stash_to_delete:
            print(f'{bcolors.RED}Error: No stash to drop.{bcolors.ENDC}')
            exit(1)
        for file in stash_to_delete:
            file_path = os.path.join(self.cache_path, file)
            os.remove(file_path)
            print(f'Dropped stash \'{file}\'.')

    def status_sos(self, args):
        wa_root = self.get_wa_root_path()

        last_update_time = self.execute_sos_command(['soscmd', 'query'], ['last_update_time'], ret_text=True, quiet=True)
        print(f'{bcolors.YELLOW}Workarea last updated at {last_update_time[0]}{bcolors.ENDC}')

        # check args
        scope_paths = []
        user_set_arg_sel = False
        for arg in args:
            if arg.startswith('-s'):
                user_set_arg_sel = True
            elif os.path.exists(arg):
                scope_paths.append(os.path.relpath(arg, wa_root))
        if not user_set_arg_sel:
            args[:0] = ['-sunm', '-sco']

        # get file info from SOS
        file_status = {}
        cur_filelist = self.execute_sos_command(['soscmd', 'status'], ['-f%C%S %P'] + args, ret_text=True, quiet=True)
        for file_info in cur_filelist:
            if file_info.startswith('*'):
                continue
            file_info = file_info.split()
            if file_info[1] in self.ign_filelist:
                continue
            file_info[1] = self.remove_prefix(file_info[1], './')

            file_attr = []
            if file_info[0][0] == '-': # check if changed
                file_attr.append('unchanged')
            elif file_info[0][0] == '!': # check if deleted
                file_attr.append('deleted')
            if file_info[0][1] == '?': # check if unmanaged
                file_attr.append('unmanaged')
            else:
                file_attr.append('checkout')
            file_status[file_info[1]] = file_attr

        # get file info from local cache
        self.setup_user_cache()
        wa_data_file_path = os.path.join(self.cache_path, self.wa_data_file)
        wa_data = {}

        if os.path.isfile(wa_data_file_path) and os.path.getsize(wa_data_file_path):
            with open(wa_data_file_path, 'r') as cache_file:
                wa_data = json.load(cache_file)
        self.init_json_hier(wa_data, dict, ['file_status'])

        for key in ['create', 'delete']:
            if key not in wa_data['file_status']:
                continue
            for item in wa_data['file_status'][key]:
                if not scope_paths or item.startswith(tuple(scope_paths)):
                    file_attr = []
                    if item in file_status:
                        file_attr = file_status[item]
                    file_attr.append(key)
                    file_status[item] = file_attr
        for key in ['move']:
            if key not in wa_data['file_status']:
                continue
            for item in wa_data['file_status'][key]:
                for subpath in wa_data['file_status'][key][item]:
                    if not scope_paths or subpath.startswith(tuple(scope_paths)):
                        file_attr = []
                        if subpath in file_status:
                            file_attr = file_status[subpath]
                        if key == 'move':
                            file_attr.append(f'{key}-')
                            file_status[subpath] = file_attr

                            target_file_path = os.path.join(item, os.path.basename(subpath))
                            file_attr = []
                            if target_file_path in file_status:
                                file_attr = file_status[target_file_path]
                            file_attr.append(f'{key}+')
                            file_status[target_file_path] = file_attr

        unmanaged_files = []
        hdr_printed = False
        for file in sorted(file_status.keys()):
            file_attr = sorted(file_status[file])
            if 'unmanaged' in file_attr and 'create' not in file_attr:
                unmanaged_files.append(file)
                continue
            if not hdr_printed:
                hdr_printed = True
                print(f'\nTracked files:')
            rel_path = os.path.relpath(os.path.join(wa_root, file), os.getcwd())
            if os.path.isdir(rel_path):
                rel_path += '/'
            file_attr = [attr for attr in file_attr if attr not in ['unmanaged']]
            prefix = file_attr.pop(0)
            suffix = f' {bcolors.GRAY}(' + ' '.join(file_attr) + f'){bcolors.ENDC}' if file_attr else ''
            print(f'  {bcolors.BLUE}[{prefix:9}]{bcolors.ENDC} ./{rel_path}{suffix}')

        if unmanaged_files:
            print(f'\nUntracked files:')
            for file in sorted(unmanaged_files):
                rel_path = os.path.relpath(os.path.join(wa_root, file), os.getcwd())
                file_attr = sorted(file_status[file])
                file_attr = [attr for attr in file_attr if attr not in ['unmanaged']]
                suffix = f' {bcolors.GRAY}(' + ' '.join(file_attr) + f'){bcolors.ENDC}' if file_attr else ''
                if os.path.isdir(rel_path):
                    rel_path += '/'
                print(f'  {bcolors.BLUE}[untracked]{bcolors.ENDC} ./{rel_path}{suffix}')

    def check_args_count(self, args, min=-1, max=-1):
        len_args = len(args)
        if min >=0 and len_args < min:
            print(f'{bcolors.RED}Error: At least {min} args needed.{bcolors.ENDC}')
            exit(1)
        if max >= 0 and len_args > max:
            print(f'{bcolors.RED}Error: At max {max} args valid.{bcolors.ENDC}')
            exit(1)

    def run_command(self, command, args):
        if command in self.commands:
            self.commands[command](args)
        else:
            print(f'{bcolors.RED}Error: Unsupported command: {command}. Run with -h for script help.{bcolors.ENDC}')
            exit(1)

    def get_wa_root_path(self):
        wa_root = self.execute_sos_command(['soscmd', 'findwaroot'], [], ret_text=True, quiet=True)
        wa_root = wa_root[0] if len(wa_root) else ''
        if not os.path.exists(wa_root):
            print(f'{bcolors.RED}Error: WA path could not be found.{bcolors.ENDC}')
            exit(1)
        return wa_root

    def execute_sos_command(self, sos_command, args, ret_text=False, ret_code=False, chk_err=True, quiet=False):
        command = sos_command + args
        if not quiet:
            print(f'{bcolors.GRAY}Run cmd: {" ".join(command)}{bcolors.ENDC}')
        #if sos_command[0] in 'soscmd' and sos_command[1] in ['co', 'ci', 'create', 'delete', 'move', 'merge', 'usebranch', 'update', 'newworkarea', 'discardco', 'deleteworkarea']:
        #    return
        try:
            result = subprocess.run(command, check=chk_err, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out_str = result.stdout.decode()
            if not quiet:
                print(out_str)
            if ret_text:
                out_str_a = out_str.splitlines()
                while out_str_a and out_str_a[0].startswith(tuple(['Invoking SOS', '!! Warning:', '** The flags'])):
                    out_str_a.pop(0)
                if ret_code:
                    return result.returncode, out_str_a
                else:
                    return out_str_a
            if ret_code:
                return result.returncode
        except subprocess.CalledProcessError as e:
            print(f'{bcolors.RED}Error: Failed to execute command: {e}{bcolors.ENDC}')
            exit(1)

    def generate_temp_filename(self, only_randstr=False):
        length = 10
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(length))
        if only_randstr:
            return random_string
        else:
            return '/tmp/ntmp_' + random_string

    def setup_user_cache(self, username=''):
        if not username:
            username = os.environ['USER']
        self.cache_path = os.path.expanduser(f'~{username}/.cache/git2sos')
        try:
            if '~' in self.cache_path:
                raise Exception(f'Invalid user: {username}')
            if not os.path.isdir(self.cache_path):
                os.makedirs(self.cache_path)
        except Exception as e:
            print(f'{bcolors.RED}Error: Could not setup cache: {e}{bcolors.ENDC}')
            exit(1)

    def init_json_hier(self, obj, type, keys):
        obj_hier = obj
        num_keys = len(keys)
        for idx, key in enumerate(keys):
            if key not in obj_hier:
                if idx == num_keys - 1:
                    obj_hier[key] = type()
                else:
                    obj_hier[key] = dict() # assuming only hierarchy of dict. if dict/list mixed, need to fix
            obj_hier = obj_hier[key]

    def remove_prefix(self, text, prefix):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text

    def get_datetime_from_str(self, arg):
        datetime_object = None
        try: # try date and time
            datetime_object = datetime.datetime.strptime(arg, '%Y/%m/%d %H:%M:%S')
        except Exception as e:
            try: #try only date
                datetime_object = datetime.datetime.strptime(arg, '%Y/%m/%d')
            except Exception as e:
                pass
        return datetime_object

    def adjust_datetime_war(self, datetime_object):
        # SOS, for some reason, adds 15 mintes to the from & to times. so pre-amp the values
        adj_from_datetime = (datetime_object + datetime.timedelta(minutes=15)).strftime('%Y/%m/%d %H:%M:%S')
        adj_to_datetime = (datetime_object - datetime.timedelta(minutes=15)).strftime('%Y/%m/%d %H:%M:%S')
        return adj_from_datetime, adj_to_datetime

    def get_latest_stash_name(self):
        stash_paths_list = []
        cache_files = os.listdir(self.cache_path)
        for file_name in cache_files:
            file_path = os.path.join(self.cache_path, file_name)
            if not os.path.isfile(file_path) or not file_name.startswith('stash_'):
                continue
            stash_paths_list.append(file_path)
        if stash_paths_list:
            stash_paths_list.sort(key=os.path.getctime)
            return os.path.basename(stash_paths_list[-1])
        return None

if __name__ == '__main__':
    wrapper = SOSWrapper()
    if len(sys.argv) > 1:
        wrapper.run_command(sys.argv[1], sys.argv[2:])
    else:
        print(f'{bcolors.RED}Error: Please provide a command. Run with -h for script help.{bcolors.ENDC}')
