import git



def files_in_repo(path):
    return (blob.path for blob in git.Repo(path).head.commit.tree.traverse())


def git_repos_at_path(path):
    return [p[:-4] for p in glob(path + '/**/.git/', recursive=True)]


def tracked_files(path):
    return reduce(
        lambda x, y: x | y,
        (set(files_in_repo(repo_path)) for repo_path in git_repos_at_path(path)))

