from tqdm import tqdm

class ProgressBar:
    def __init__(self, total):
        self.pbar = tqdm(total=total, ncols=80)

    def update(self, n):
        self.pbar.n = n
        self.pbar.refresh()
        if n == self.pbar.total:
            self.pbar.close() 