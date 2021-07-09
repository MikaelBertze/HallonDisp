from tkinter import Canvas


class Graph(Canvas):
    def __init__(self, height, width, parent):
        Canvas.__init__(self, parent, height=height, width=width, bg="#333")
        self.height = height
        self.width = width

    def plot(self, y, x):
        # axis
        self.create_line(5, 5 , 5, self.height - 5, self.width - 5, self.height - 5, width=5, fill='red')
        x_len = self.width - 10
        y_len = self.height - 10

        if len(x) > x_len:
            #sample byt creating mean values
            x = [int(sum(x) / len(x)) for x in Graph.chunks(x, x_len)]



    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
