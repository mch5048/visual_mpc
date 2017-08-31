import numpy as np
from matplotlib import animation
import matplotlib.gridspec as gridspec

import pdb
import cPickle

import Tkinter as Tk

from Tkinter import Button, Frame, Canvas, Scrollbar
import Tkconstants

from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

frame = None
canvas = None



def plot_psum_overtime(gen_distrib, n_exp, filename):
    plt.figure(figsize=(25, 2),dpi=80)

    for ex in range(n_exp):
        psum = []
        plt.subplot(1,n_exp, ex+1)
        for t in range(len(gen_distrib)):
            psum.append(np.sum(gen_distrib[t][ex]))

        psum = np.array(psum)
        plt.plot(range(len(gen_distrib)), psum)
        plt.ylim([0,2.5])

    # plt.show()
    plt.savefig(filename + "/psum.png")
    plt.close('all')

t = 0
class Visualizer_tkinter(object):
    def __init__(self, dict_ = None, append_masks = True, gif_savepath=None, numex = 4, suf= ""):

        if dict_ == None:
            dict_ = cPickle.load(open(gif_savepath + '/pred.pkl', "rb"))

        gen_images = dict_['gen_images']
        self.iternum = dict_['iternum']

        if gen_images[0].shape[0] < numex:
            raise ValueError("batchsize too small for providing desired number of exmaples!")

        self.numex = numex
        self.video_list = []

        if 'ground_truth' in dict_:
            ground_truth = dict_['ground_truth']
            if not isinstance(ground_truth, list):
                ground_truth = np.split(ground_truth, ground_truth.shape[1], axis=1)
                ground_truth = [np.squeeze(g) for g in ground_truth]
            ground_truth = ground_truth[1:]

            self.video_list.append((ground_truth, 'Ground Truth'))

        self.video_list.append((gen_images, 'Gen Images'))

        if 'gen_distrib' in dict_:
            gen_pix_distrib = dict_['gen_distrib']
            plot_psum_overtime(gen_pix_distrib, numex, gif_savepath)
            self.video_list.append((gen_pix_distrib, 'Gen distrib'))

        if append_masks:
            gen_masks = dict_['gen_masks']
            gen_masks = convert_to_videolist(gen_masks, repeat_last_dim=False)

            for i,m in enumerate(gen_masks):
                self.video_list.append((m,'mask {}'.format(i)))

        if 'moved_parts' in dict_:
            moved_parts = dict_['moved_parts']
            moved_parts = convert_to_videolist(moved_parts, repeat_last_dim=False)

            for i, m in enumerate(moved_parts):
                self.video_list.append((m, 'moved part {}'.format(i)))

        if 'moved_images' in dict_:
            moved_images = dict_['moved_images']
            moved_images = convert_to_videolist(moved_images, repeat_last_dim=False)

            for i, m in enumerate(moved_images):
                self.video_list.append((m, 'moved image {}'.format(i)))

        if 'moved_bckgd' in dict_:
            moved_bckgd = dict_['moved_bckgd']
            moved_bckgd = convert_to_videolist(moved_bckgd, repeat_last_dim=False)

            for i, m in enumerate(moved_bckgd):
                self.video_list.append((m, 'moved_bckgd {}'.format(i)))

        # if 'flow_vectors' in dict_:
        #     self.videolist.append(visualize_flow(dict_))
        self.renormalize_heatmaps = False
        print 'renormalizing heatmaps: ', self.renormalize_heatmaps

        self.gif_savepath = gif_savepath
        self.t = 0

        self.suf = suf
        self.append_masks = append_masks
        self.build_figure()

    def build_figure(self):

        self.num_rows = len(self.video_list)

        # plot each markevery case for linear x and y scales
        root = Tk.Tk()
        root.rowconfigure(1, weight=1)
        root.columnconfigure(1, weight=1)

        frame = Frame(root)
        frame.grid(column=1, row=1, sticky=Tkconstants.NSEW)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(1, weight=1)

        standard_size = np.array([1.5 * self.numex, self.num_rows * 1.5])
        # standard_size = np.array([6, 24])
        figsize = (standard_size * 1.0).astype(np.int)
        fig = plt.figure(num=1, figsize=figsize)

        self.addScrollingFigure(fig, frame)

        buttonFrame = Frame(root)
        buttonFrame.grid(row=1, column=2, sticky=Tkconstants.NS)
        biggerButton = Button(buttonFrame, text="larger",
                              command=lambda: self.changeSize(fig, 1.5))
        biggerButton.grid(column=1, row=1)
        smallerButton = Button(buttonFrame, text="smaller",
                               command=lambda: self.changeSize(fig, .5))
        smallerButton.grid(column=1, row=2)

        axes_list = []
        l = []

        for vid in self.video_list:
            l.append(len(vid[0]))
        tlen = np.min(np.array(l))
        print 'minimum video length',tlen

        outer_grid = gridspec.GridSpec(self.num_rows, 1)

        drow = 1./self.num_rows

        self.im_handle_list = []
        for row in range(self.num_rows):
            inner_grid = gridspec.GridSpecFromSubplotSpec(1, self.numex,
                                                          subplot_spec=outer_grid[row], wspace=0.0, hspace=0.0)
            image_row = self.video_list[row][0]

            im_handle_row = []
            for col in range(self.numex):
                ax = plt.Subplot(fig, inner_grid[col])
                ax.set_xticks([])
                ax.set_yticks([])
                axes_list.append(fig.add_subplot(ax))
                # if row==0:
                #     axes_list[-1].set_title('example {}'.format(col))

                if image_row[0][col].shape[-1] == 1:

                    im_handle = axes_list[-1].imshow(np.squeeze(image_row[0][col]),
                                                     zorder=0, cmap=plt.get_cmap('jet'),
                                                     interpolation='none',
                                                     animated=True)
                else:
                    im_handle = axes_list[-1].imshow(image_row[0][col], interpolation='none',
                                                     animated=True)

                im_handle_row.append(im_handle)
            self.im_handle_list.append(im_handle_row)

            plt.figtext(.5, 1-(row*drow*0.995)-0.003, self.video_list[row][1], va="center", ha="center", size=8)

        plt.axis('off')
        fig.tight_layout()

        # Set up formatting for the movie files
        Writer = animation.writers['imagemagick_file']
        writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)

        # call the animator.  blit=True means only re-draw the parts that have changed.
        anim = animation.FuncAnimation(fig, self.animate,
                                       fargs= [self.im_handle_list, self.video_list, self.numex, self.num_rows, tlen],
                                       frames=tlen, interval=200, blit=True)

        if self.append_masks:
            self.suf = '_masks'+self.suf
        if self.gif_savepath != None:
            filepath = self.gif_savepath + '/animation{}{}.gif'.format(self.iternum,self.suf)
            print 'saving gif under: ', filepath
            anim.save(filepath, writer='imagemagick')
        root.mainloop()

    def changeSize(self, figure, factor):
        global canvas, mplCanvas, interior, interior_id, frame, cwid
        oldSize = figure.get_size_inches()
        print("old size is", oldSize)
        figure.set_size_inches([factor * s for s in oldSize])
        wi, hi = [i * figure.dpi for i in figure.get_size_inches()]
        print("new size is", figure.get_size_inches())
        print("new size pixels: ", wi, hi)
        mplCanvas.config(width=wi, height=hi)
        printBboxes("A")
        # mplCanvas.grid(sticky=Tkconstants.NSEW)
        canvas.itemconfigure(cwid, width=wi, height=hi)
        printBboxes("B")
        canvas.config(scrollregion=canvas.bbox(Tkconstants.ALL), width=200, height=200)
        figure.canvas.draw()
        printBboxes("C")
        print()

    def addScrollingFigure(self, figure, frame):
        global canvas, mplCanvas, interior, interior_id, cwid
        # set up a canvas with scrollbars
        canvas = Canvas(frame)
        canvas.grid(row=1, column=1, sticky=Tkconstants.NSEW)

        xScrollbar = Scrollbar(frame, orient=Tkconstants.HORIZONTAL)
        yScrollbar = Scrollbar(frame)

        xScrollbar.grid(row=2, column=1, sticky=Tkconstants.EW)
        yScrollbar.grid(row=1, column=2, sticky=Tkconstants.NS)

        canvas.config(xscrollcommand=xScrollbar.set)
        xScrollbar.config(command=canvas.xview)
        canvas.config(yscrollcommand=yScrollbar.set)
        yScrollbar.config(command=canvas.yview)

        # plug in the figure
        figAgg = FigureCanvasTkAgg(figure, canvas)
        mplCanvas = figAgg.get_tk_widget()
        # mplCanvas.grid(sticky=Tkconstants.NSEW)

        # and connect figure with scrolling region
        cwid = canvas.create_window(0, 0, window=mplCanvas, anchor=Tkconstants.NW)
        printBboxes("Init")
        canvas.config(scrollregion=canvas.bbox(Tkconstants.ALL), width=200, height=200)

    def animate(self, *args):
        global t
        _, im_handle_list, video_list, num_ex, num_rows, tlen = args

        artistlist = []
        for row in range(num_rows):
            image_row = video_list[row][0]
            for col in range(num_ex):

                if image_row[0][col].shape[-1] == 1: # if visualizing with single-channel heatmap
                    im = np.squeeze(image_row[t][col])
                    if self.renormalize_heatmaps:
                        im = im/(np.max(im)+1e-5)
                    im_handle_list[row][col].set_array(im)
                else:
                    im_handle_list[row][col].set_array(image_row[t][col])
            artistlist += im_handle_list[row]

        # print 'update at t', t
        t += 1

        if t == tlen:
            t = 0

        return artistlist

def printBboxes(label=""):
  global canvas, mplCanvas, interior, interior_id, cwid
  print("  "+label,
    "canvas.bbox:", canvas.bbox(Tkconstants.ALL),
    "mplCanvas.bbox:", mplCanvas.bbox(Tkconstants.ALL))



def convert_to_videolist(input, repeat_last_dim):
    tsteps = len(input)
    nmasks = len(input[0])

    list_of_videos = []

    for m in range(nmasks):  # for timesteps
        video = []
        for t in range(tsteps):
            if repeat_last_dim:
                single_mask_batch = np.repeat(input[t][m], 3, axis=3)
            else:
                single_mask_batch = input[t][m]
            video.append(single_mask_batch)
        list_of_videos.append(video)

    return list_of_videos


if __name__ == '__main__':
    # file_path = '/home/frederik/Documents/catkin_ws/src/visual_mpc/tensorflow_data/sawyer/cdna_history/modeldata'
    file_path = '/home/frederik/Documents/catkin_ws/src/visual_mpc/tensorflow_data/sawyer/move_1stbckgd_cdna/modeldata'
    v  = Visualizer_tkinter(append_masks=True, gif_savepath=file_path)