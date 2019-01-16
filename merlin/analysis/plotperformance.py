import os
from matplotlib import pyplot as plt
from matplotlib import patches
import merlin
plt.style.use(
        os.sep.join([os.path.dirname(merlin.__file__),
                     'ext', 'default.mplstyle']))
import seaborn
import numpy as np

from merlin.core import analysistask
from merlin.util import binary

class PlotPerformance(analysistask.AnalysisTask):

    """
    An analysis task that generates plots depicting metrics of the MERFISH
    decoding.
    """

    # TODO all the plotting should be refactored. I do not like the way
    # this class is structured as a long list of plotting functions. It would
    # be more convenient if each plot could track it's dependent tasks and
    # be executed once those tasks are complete.

    def __init__(self, dataSet, parameters=None, analysisName=None):
        super().__init__(dataSet, parameters, analysisName)

        #TODO - move this definition to run_analysis()
        self.optimizeTask = self.dataSet.load_analysis_task(
                self.parameters['optimize_task'])
        self.decodeTask = self.dataSet.load_analysis_task(
                self.parameters['decode_task'])
        self.filterTask = self.dataSet.load_analysis_task(
                self.parameters['filter_task'])
        if 'segment_task' in self.parameters:
            self.segmentTask = self.dataSet.load_analysis_task(
                    self.parameters['segment_task'])
        else:
            self.segmentTask = None

    def get_estimated_memory(self):
        return 30000

    def get_estimated_time(self):
        return 180

    def get_dependencies(self):
        return [self.parameters['decode_task'], self.parameters['filter_task']]

    # TODO - the functions in this class have too much repeated code
    # TODO - for the following 4 plots, I can add a line indicating the
    # barcode selection thresholds.
    def _plot_barcode_intensity_distribution(self):
        bcIntensities = self.decodeTask.get_barcode_database() \
                .get_barcode_intensities()
        fig = plt.figure(figsize=(4,4))
        plt.hist(np.log10(bcIntensities), bins=500)
        plt.xlabel('Mean intensity ($log_{10}$)')
        plt.ylabel('Count')
        plt.title('Intensity distribution for all barcodes')
        plt.tight_layout(pad=0.2)
        self.dataSet.save_figure(self, fig, 'barcode_intensity_distribution')

    def _plot_barcode_area_distribution(self):
        bcAreas = self.decodeTask.get_barcode_database() \
                .get_barcode_areas()
        fig = plt.figure(figsize=(4,4))
        plt.hist(bcAreas, bins=np.arange(15))
        plt.xlabel('Barcode area (pixels)')
        plt.ylabel('Count')
        plt.title('Area distribution for all barcodes')
        plt.xticks(np.arange(15))
        plt.tight_layout(pad=0.2)
        self.dataSet.save_figure(self, fig, 'barcode_area_distribution')

    def _plot_barcode_distance_distribution(self):
        bcDistances = self.decodeTask.get_barcode_database() \
                .get_barcode_distances()
        fig = plt.figure(figsize=(4,4))
        plt.hist(bcDistances, bins=500)
        plt.xlabel('Barcode distance')
        plt.ylabel('Count')
        plt.title('Distance distribution for all barcodes')
        plt.tight_layout(pad=0.2)
        self.dataSet.save_figure(self, fig, 'barcode_distance_distribution')

    def _plot_barcode_intensity_area_violin(self):
        barcodeDB = self.decodeTask.get_barcode_database()
        intensityData = [np.log10(
            barcodeDB.get_intensities_for_barcodes_with_area(x)) \
                    for x in range(1, 15)]
        fig = plt.figure(figsize=(8, 4))
        # This will cause an error if one of the lists in intensity data
        # is empty.
        plt.violinplot(intensityData, showextrema=False, showmedians=True)
        plt.axvline(x=self.filterTask.parameters['area_threshold']-0.5,
                color='green', linestyle=':')
        plt.axhline(y=np.log10(
            self.filterTask.parameters['intensity_threshold']),
                color='green', linestyle=':')
        plt.xlabel('Barcode area (pixels)')
        plt.ylabel('Mean intensity ($log_{10}$)')
        plt.title('Intensity distribution by barcode area')
        plt.tight_layout(pad=0.2)
        self.dataSet.save_figure(self, fig, 'barcode_intensity_area_violin')

    def _plot_bitwise_intensity_violin(self):
        bc = self.filterTask.get_barcode_database().get_barcodes()
        bitCount = self.dataSet.get_bit_count()

        zeroBitSet = [[i for i,x in zip(
                        bc['intensity_' + str(j)], bc['barcode']) \
                    if not binary.k_bit_set(x, j)] for j in range(bitCount)]
        oneBitSet = [[i for i,x in zip(
                        bc['intensity_' + str(j)], bc['barcode']) \
                    if binary.k_bit_set(x, j)] for j in range(bitCount)]

        fig = plt.figure(figsize=(15,5))
        zeroViolin = plt.violinplot(
                zeroBitSet, np.arange(bitCount)-0.15, widths=0.3, 
                showmedians=True)
        zeroPatch = patches.Patch(
                color=zeroViolin['bodies'][0].get_facecolor()[0], label='0')
        oneViolin = plt.violinplot(
                oneBitSet, np.arange(bitCount)+0.15, widths=0.3, 
                showmedians=True)
        onePatch = patches.Patch(
                color=oneViolin['bodies'][0].get_facecolor()[0], label='1')
        plt.xticks(np.arange(bitCount))
        plt.xlabel('Bit index')
        plt.ylabel('Normalized and scaled intensity')
        plt.title('Bit-wise intensity distributions for filtered barcodes')
        self.dataSet.save_figure(self, fig, 'barcode_bitwise_intensity_violin')

    def _plot_blank_distribution(self):
        codebook = self.dataSet.get_codebook()
        bc = self.filterTask.get_barcode_database().get_barcodes()
        minX = np.min(bc['global_x'])
        minY = np.min(bc['global_y'])
        maxX = np.max(bc['global_x'])
        maxY = np.max(bc['global_y'])

        blankIDs = codebook.get_blank_indexes()
        blankBC = bc[bc['barcode_id'].isin(blankIDs)]

        fig = plt.figure(figsize=(10,10))
        ax = fig.add_subplot(111)
        h = ax.hist2d(blankBC['global_x'], blankBC['global_y'],
            bins=(np.ceil(maxX-minX)/5, np.ceil(maxY-minY)/5),
            cmap=plt.get_cmap('Greys'))
        cbar = plt.colorbar(h[3], ax=ax)
        cbar.set_label('Spot count', rotation=270)
        ax.set_aspect('equal', 'datalim')
        plt.xlabel('X position (microns)')
        plt.ylabel('Y position (microns)')
        plt.title('Spatial distribution of blank barcodes')
        self.dataSet.save_figure(self, fig, 'blank_spatial_distribution')

    def _plot_matched_barcode_distribution(self):
        codebook = self.dataSet.get_codebook()
        bc = self.filterTask.get_barcode_database().get_barcodes()
        minX = np.min(bc['global_x'])
        minY = np.min(bc['global_y'])
        maxX = np.max(bc['global_x'])
        maxY = np.max(bc['global_y'])

        codingIDs = codebook.get_coding_indexes()
        codingBC = bc[bc['barcode_id'].isin(codingIDs)]

        fig = plt.figure(figsize=(10,10))
        ax = fig.add_subplot(111)
        h = ax.hist2d(codingBC['global_x'], codingBC['global_y'],
            bins=(np.ceil(maxX-minX)/5, np.ceil(maxY-minY)/5),
            cmap=plt.get_cmap('Greys'))
        cbar = plt.colorbar(h[3], ax=ax)
        cbar.set_label('Spot count', rotation=270)
        ax.set_aspect('equal', 'datalim')
        plt.xlabel('X position (microns)')
        plt.ylabel('Y position (microns)')
        plt.title('Spatial distribution of identified barcodes')
        self.dataSet.save_figure(self, fig, 'barcode_spatial_distribution')

    def _plot_cell_segmentation(self):
        cellBoundaries = self.segmentTask.get_cell_boundaries()

        fig = plt.figure(figsize=(10,10))
        ax = fig.add_subplot(111)
        ax.set_aspect('equal', 'datalim')

        def plot_cell_boundary(boundary):
            ax.plot([x[0] for x in boundary], [x[1] for x in boundary])
        cellPlots = [plot_cell_boundary(b) for b in cellBoundaries]

        plt.xlabel('X position (microns)')
        plt.ylabel('Y position (microns)')
        plt.title('Cell boundaries')
        self.dataSet.save_figure(self, fig, 'cell_boundaries')

    def _plot_optimization_scale_factors(self):
        fig = plt.figure(figsize=(5,5))
        seaborn.heatmap(self.optimizeTask.get_scale_factor_history())
        plt.xlabel('Bit index')
        plt.ylabel('Iteration number')
        plt.title('Scale factor optimization history')
        self.dataSet.save_figure(self, fig, 'optimization_scale_factors')

    def _plot_optimization_barcode_counts(self):
        fig = plt.figure(figsize=(5,5))
        seaborn.heatmap(self.optimizeTask.get_barcode_count_history())
        plt.xlabel('Barcode index')
        plt.ylabel('Iteration number')
        plt.title('Barcode counts optimization history')
        self.dataSet.save_figure(self, fig, 'optimization_barcode_counts')

    def _plot_barcode_abundances(self, barcodes, outputName):
        uniqueBarcodes = np.unique(barcodes['barcode_id'])
        bcCounts = [len(barcodes[barcodes['barcode_id']==x]) \
                for x in uniqueBarcodes]

        codebook = self.dataSet.get_codebook()
        blankIDs = codebook.get_blank_indexes()

        sortedIndexes = np.argsort(bcCounts)[::-1]
        fig = plt.figure(figsize=(12,5))
        barList = plt.bar(np.arange(len(bcCounts)), 
                height=np.log10([bcCounts[x] for x in sortedIndexes]), 
                width=1, color=(0.2, 0.2, 0.2))
        for i,x in enumerate(sortedIndexes):
            if x in blankIDs:
                barList[i].set_color('r')
        plt.xlabel('Sorted barcode index')
        plt.ylabel('Count (log10)')
        plt.title('Abundances for coding (gray) and blank (red) barcodes')

        self.dataSet.save_figure(self, fig, outputName)

    def _plot_all_barcode_abundances(self):
        bc = self.decodeTask.get_barcode_database().get_barcodes()
        self._plot_barcode_abundances(bc, 'all_barcode_abundances')

    def _plot_filtered_barcode_abundances(self):
        bc = self.filterTask.get_barcode_database().get_barcodes()
        self._plot_barcode_abundances(bc, 'flitered_barcode_abundances')

    def run_analysis(self):
        self._plot_barcode_intensity_distribution()
        self._plot_barcode_area_distribution()
        self._plot_barcode_distance_distribution()
        self._plot_barcode_intensity_area_violin()
        self._plot_blank_distribution()
        self._plot_matched_barcode_distribution()
        self._plot_optimization_scale_factors()
        self._plot_optimization_barcode_counts()
        self._plot_all_barcode_abundances()
        self._plot_filtered_barcode_abundances()
        if self.segmentTask is not None:
            self._plot_cell_segmentation()
        # TODO _ analysis run times
        # TODO - barcode correlation plots
        # TODO - alignment error plots - need to save transformation information
        # first
        # TODO - barcode size spatial distribution global and FOV average
        # TODO - barcode distance spatial distribution global and FOV average
        # TODO - barcode intensity spatial distribution global and FOV average
        # TODO - good barcodes/blanks per cell
