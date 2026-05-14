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

    def is_repository(self, path):
        git_path = os.path.join(path, '.git')
        if os.path.exists(git_path):
            return True
        try:
            pygit2.Repository(path)
            return True
        except KeyError:
            return False
