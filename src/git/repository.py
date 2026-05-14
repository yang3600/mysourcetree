import os
import pygit2


class GitRepository:
    def __init__(self, path=None):
        self.path = path
        self.repo = None

    def create(self, path, bare=False):
        if not os.path.exists(path):
            os.makedirs(path)

        if bare:
            repo_path = path
        else:
            repo_path = os.path.join(path, '.git')

        repo = pygit2.init_repository(repo_path, bare=bare)
        self.repo = repo
        self.path = path
        return repo

    def open(self, path=None):
        if path is None:
            path = self.path

        if path is None:
            raise ValueError("No path provided")

        try:
            self.repo = pygit2.Repository(path)
            self.path = path
            return self.repo
        except KeyError:
            raise ValueError(f"Not a valid git repository: {path}")

    def get_status(self):
        if self.repo is None:
            raise ValueError("No repository opened")

        status = {}
        for filepath, flags in self.repo.status().items():
            status[filepath] = {
                'staged': bool(flags & pygit2.GIT_STATUS_INDEX_NEW or
                              flags & pygit2.GIT_STATUS_INDEX_MODIFIED or
                              flags & pygit2.GIT_STATUS_INDEX_DELETED),
                'modified': bool(flags & pygit2.GIT_STATUS_WT_MODIFIED),
                'untracked': bool(flags & pygit2.GIT_STATUS_WT_NEW),
                'deleted': bool(flags & pygit2.GIT_STATUS_WT_DELETED)
            }
        return status

    def stage_file(self, filepath):
        if self.repo is None:
            raise ValueError("No repository opened")

        index = self.repo.index
        index.add(filepath)
        index.write()

    def stage_all(self):
        if self.repo is None:
            raise ValueError("No repository opened")

        index = self.repo.index
        index.add_all()
        index.write()

    def unstage_file(self, filepath):
        if self.repo is None:
            raise ValueError("No repository opened")

        head = self.repo.head.peel()
        index = self.repo.index
        index.remove(filepath)
        index.write()

    def unstage_all(self):
        if self.repo is None:
            raise ValueError("No repository opened")

        index = self.repo.index
        index.clear()
        index.write()

    def commit(self, message, author_name=None, author_email=None):
        if self.repo is None:
            raise ValueError("No repository opened")

        if author_name is None:
            config = self.repo.config
            author_name = config.get("user.name", "Unknown")
            author_email = config.get("user.email", "unknown@example.com")

        author = pygit2.Signature(author_name, author_email)
        committer = pygit2.Signature(author_name, author_email)

        tree = self.repo.index.write_tree()

        parents = []
        if self.repo.head.is_valid:
            parents.append(self.repo.head.peel())

        commit = self.repo.create_commit(
            'refs/heads/' + self.repo.head.shorthand,
            author,
            committer,
            message,
            tree,
            parents
        )
        return commit

    def get_commits(self, max_count=100):
        if self.repo is None:
            raise ValueError("No repository opened")

        commits = []
        for commit in self.repo.walk(self.repo.head.target, pygit2.GIT_SORT_TIME):
            commits.append({
                'id': str(commit.id),
                'message': commit.message,
                'author': commit.author.name,
                'email': commit.author.email,
                'time': commit.commit_time,
                'parents': [str(p.id) for p in commit.parents]
            })
            if len(commits) >= max_count:
                break

        return commits

    def get_branches(self):
        if self.repo is None:
            raise ValueError("No repository opened")

        branches = {
            'local': [],
            'remote': []
        }

        for branch in self.repo.branches:
            if branch.startswith('refs/heads/'):
                branches['local'].append(branch.replace('refs/heads/', ''))
            elif branch.startswith('refs/remotes/'):
                branches['remote'].append(branch.replace('refs/remotes/', ''))

        return branches

    def create_branch(self, name, commit_id=None):
        if self.repo is None:
            raise ValueError("No repository opened")

        if commit_id is None:
            commit = self.repo.head.peel()
        else:
            commit = self.repo.get(commit_id)

        branch = self.repo.create_branch(name, commit)
        return branch

    def checkout_branch(self, branch_name):
        if self.repo is None:
            raise ValueError("No repository opened")

        branch = self.repo.branches[branch_name]
        checkout = self.repo.checkout(branch)
        return checkout

    def get_current_branch(self):
        if self.repo is None:
            raise ValueError("No repository opened")

        if self.repo.head.is_detached:
            return None

        return self.repo.head.shorthand

    def get_diff(self, filepath=None):
        if self.repo is None:
            raise ValueError("No repository opened")

        diff = self.repo.diff('HEAD', filepath)
        return diff

    def pull(self, remote_name="origin", branch=None):
        if self.repo is None:
            raise ValueError("No repository opened")

        if branch is None:
            branch = self.repo.head.shorthand

        remote = self.repo.remotes[remote_name]
        remote.fetch()

        remote_ref = f"refs/remotes/{remote_name}/{branch}"
        if remote_ref not in self.repo.references:
            raise ValueError(f"Remote branch not found: {remote_name}/{branch}")

        remote_commit = self.repo.references[remote_ref].peel()
        self.repo.merge(remote_commit.id)

        return True

    def push(self, remote_name="origin", branch=None):
        if self.repo is None:
            raise ValueError("No repository opened")

        if branch is None:
            branch = self.repo.head.shorthand

        remote = self.repo.remotes[remote_name]
        remote.push([f"refs/heads/{branch}"])

        return True

    def fetch(self, remote_name="origin"):
        if self.repo is None:
            raise ValueError("No repository opened")

        remote = self.repo.remotes[remote_name]
        remote.fetch()

        return True

    def merge(self, branch_name):
        if self.repo is None:
            raise ValueError("No repository opened")

        if branch_name not in self.repo.branches:
            raise ValueError(f"Branch not found: {branch_name}")

        branch = self.repo.branches[branch_name]
        commit = branch.peel()
        self.repo.merge(commit.id)

        return True

    def stash(self, message="WIP"):
        if self.repo is None:
            raise ValueError("No repository opened")

        self.repo.stash()
        return True

    def create_tag(self, name, message=None, commit_id=None):
        if self.repo is None:
            raise ValueError("No repository opened")

        if commit_id is None:
            commit = self.repo.head.peel()
        else:
            commit = self.repo.get(commit_id)

        if message:
            tag = self.repo.create_tag(
                name,
                commit.id,
                pygit2.GIT_OBJ_COMMIT,
                self._get_signature(),
                message
            )
        else:
            tag = self.repo.create_tag(
                name,
                commit.id,
                pygit2.GIT_OBJ_COMMIT
            )

        return tag

    def get_tags(self):
        if self.repo is None:
            raise ValueError("No repository opened")

        tags = []
        for tag in self.repo.tags:
            tags.append(tag)

        return tags

    def _get_signature(self):
        config = self.repo.config
        name = config.get("user.name", "Unknown")
        email = config.get("user.email", "unknown@example.com")
        return pygit2.Signature(name, email)

    def is_repository(self, path):
        git_path = os.path.join(path, '.git')
        if os.path.exists(git_path):
            return True
        try:
            pygit2.Repository(path)
            return True
        except KeyError:
            return False
