import pickle as pkl
import os.path as osp
import os
import numpy as np
import pylab as plt
from scipy.stats import gaussian_kde, pearsonr, spearmanr
from scipy.special import kl_div
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics import r2_score
from props_list import get_prop_labels

import matex.blt.configs.config as config


def load_eval_data(prop, path, method='bilinear'):
    eval_data = {}

    ood_file = os.path.join(path, f'{method}_eval_ood.pkl')
    in_dist_file = os.path.join(path, f'{method}_eval_in_dist.pkl')

    try:
        with open(ood_file, 'rb') as f:
            ood_data = pkl.load(f)
            ood_preds = ood_data['preds']
            ood_gt = ood_data['gt']

        with open(in_dist_file, 'rb') as f:
            in_dist_data = pkl.load(f)
            in_dist_preds = in_dist_data['preds']
            in_dist_gt = in_dist_data['gt']

        # Store data for the current property
        eval_data[prop] = {
            'ood': {'preds': ood_preds, 'gt': ood_gt},
            'in_dist': {'preds': in_dist_preds, 'gt': in_dist_gt}
        }

        print(f"Successfully loaded data for {prop}")
    except FileNotFoundError as e:
        print(f"File not found for, {prop}: {e}")
    except Exception as e:
        print(f"Error loading data for, {prop}: {e}")

    return eval_data


def kde_dist(path, eval_data, prop, x_label, method='bilinear'):
    """
    Generate a KDE plot for method OOD predictions

    Args:
        path (str): Directory to save the KDE plot.
        eval_data (dict): Dictionary containing predictions and ground truth for method.
        prop (str): Property name to label the plot.
    """
    plt.close('all')
    plt.figure(figsize=(9, 8))

    # Extract data for KDE and convert to NumPy arrays for processing
    ground_truth = np.array(eval_data['bilinear'][prop]['ood']['gt'])
    ood_preds = np.array(eval_data[method][prop]['ood']['preds'])

    # Define shared range for the KDE plot
    min_value = min(ground_truth.min(), ood_preds.min())
    max_value = max(ground_truth.max(), ood_preds.max())
    steps = 1000
    x = np.linspace(min_value, max_value, steps)

    # Compute KDEs
    kde_gt = gaussian_kde(ground_truth.squeeze())
    kde_preds = gaussian_kde(ood_preds.squeeze())

    # Plot KDEs
    plt.fill_between(x, kde_gt(x), color='red', alpha=0.5, label='Ground Truth')
    plt.fill_between(x, kde_preds(x), color='magenta', alpha=0.5, label='Ours')

    # Add labels, title, legend, and save the plot
    plt.ylabel('Probability Density', fontsize=22)
    plt.xlabel(f'{x_label}', fontsize=22)
    plt.legend(fontsize=20, loc='best')
    plt.title(f'OOD Property Value Prediction KDE Plot', fontsize=28)
    plt.ylim(bottom=0)
    plt.tick_params(axis='both', labelsize=18)
    plt.savefig(osp.join(path, 'ood_kde_compare.png'), bbox_inches='tight', dpi=300)
    print(f"KDE plot saved at: {osp.join(path, 'ood_kde_compare.png')}")


def pca_plot(benchmark, prop, rep_file, path, title):
    """
    Plots PCA projection of the data representation.
    """

    # Load data
    data_path = osp.join(config.DATA_DIR, benchmark, prop, f'demos_{rep_file}.pkl')
    with open(data_path, 'rb') as f:
        data = pkl.load(f)
    
    # Combine data for PCA fitting
    data_all = np.concatenate((data['train_X'], data['eval_X'], data['ood_X']), axis=0)
    
    # PCA
    data_all = np.concatenate((data['train_X'], data['eval_X'], data['ood_X']), axis=0)
    pca = PCA(n_components=2).fit(data_all)
    transformed_data = {key: pca.transform(data[key]) for key in ['train_X', 'eval_X', 'ood_X']}
    print(f"Explained Variance Ratios: PC1: {pca.explained_variance_ratio_[0]:.2f}, "
          f"PC2: {pca.explained_variance_ratio_[1]:.2f}")

    # Print explained variance
    print(f'Variance from PC 0: {pca.explained_variance_ratio_[0]:.2f}')
    print(f'Variance from PC 1: {pca.explained_variance_ratio_[1]:.2f}')
    
    # Create the plot
    fig, ax_pca = plt.subplots(figsize=(10, 8))
    ax_pca.scatter(transformed_data[:, 0], transformed_data[:, 1], c='silver', label='Training data', edgecolor='face')
    ax_pca.scatter(transformed_data[:, 0], transformed_data[:, 1], c='gray', label='ID samples', edgecolor='face')
    ax_pca.scatter(transformed_data[:, 0], transformed_data[:, 1], c='tomato', label='OOD data', edgecolor='face')

    # Format the plot
    ax_pca.set_xlabel('PCA Component 1', fontsize=14)
    ax_pca.set_ylabel('PCA Component 2', fontsize=14)
    ax_pca.set_title(f'PCA Projection of Data Representation for {title}', fontsize=16)
    ax_pca.legend(fontsize=12)
    ax_pca.grid(True)

    # Save the plot
    plt.tight_layout()
    save_path = osp.join(path, 'PCA_proj.png')
    plt.savefig(save_path, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"PCA plot saved at: {save_path}")


def tsne_plot(path, datapath):
    """ 
    Plots t-SNE of material representations (X) based on ALL data
    """
    with open(datapath, 'rb') as input_file:
        all_data = pkl.load(input_file)
    tsne = TSNE(n_components=2, learning_rate='auto', init='random', perplexity=3)
    X_embedded = tsne.fit_transform(np.concatenate([all_data['train_X'], all_data['eval_X'], all_data['ood_X']])) #train, in dist, ood
    plt.close('all')
    plt.figure()
    nX, nE = len(all_data['train_X']), len(all_data['eval_X'])
    plt.scatter(X_embedded[:nX,0], X_embedded[:nX,1], alpha=0.5, label='train')
    plt.scatter(X_embedded[nX:nX+nE,0], X_embedded[nX:nX+nE,1], alpha=0.5, label='in dist')
    plt.scatter(X_embedded[nX+nE:,0], X_embedded[nX+nE:,1], alpha=0.5, label='ood')
    plt.legend()
    plt.savefig(osp.join(path, 'tsne_Xs.png'), bbox_inches='tight', dpi=300)


def parity_plot(eval_data, prop, logdir, method='bilinear', x_label="Property"):
    """
    Generate a figure with method's parity plot.

    Args:
        eval_data (dict): Dictionary containing method's prediction data.
        prop (str): Property name for setting axis limits.
        logdir (str): Directory to save the plots.
        x_label (str): Label for the x-axis (default: "Property").
    """
    def plot_parity(ax, gt, preds, mae, color, label_prefix):
        """Helper function to plot scatter and add parity line."""
        ax.scatter(gt, preds, label=f'{label_prefix} MAE {round(mae, 2)}', color=color)
        ax.axline((0, 0), (1, 1), linewidth=2, color='black')

    def set_plot_limits(ax, gt_bilinear_id=None, gt_bilinear_ood=None):
        """Dynamically set axis limits based on gt values from bilinear data."""
        gt_bilinear_id = gt_bilinear_id.flatten()
        gt_bilinear_ood = gt_bilinear_ood.flatten()
        lower_limit = np.min(gt_bilinear_id) - 0.05 * abs(np.min(gt_bilinear_id))  # Add buffer below
        upper_limit = np.max(gt_bilinear_ood) + 0.05 * abs(np.max(gt_bilinear_ood))  # Add buffer above
        
        ax.set_xlim(lower_limit, upper_limit)
        ax.set_ylim(lower_limit, upper_limit)

    # Create a grid of subplots
    fig, ax = plt.subplots(1, 1, figsize=(8, 8), sharey=True)
    if "bilinear" in eval_data:
        gt_bilinear_id = np.array(eval_data["bilinear"][prop]["in_dist"]["gt"])
        gt_bilinear_ood = np.array(eval_data["bilinear"][prop]["ood"]["gt"])

    data = eval_data[method][prop]
    in_dist_gt = np.array(data["in_dist"]["gt"]).flatten()
    in_dist_preds = np.array(data["in_dist"]["preds"]).flatten()
    ood_gt = np.array(data["ood"]["gt"]).flatten()
    ood_preds = np.array(data["ood"]["preds"]).flatten()

    # Compute metrics
    mae_id = np.mean(np.abs(in_dist_gt - in_dist_preds))
    mae_ood = np.mean(np.abs(ood_gt - ood_preds))
    ood_thres = np.min(ood_gt)
    TP = np.sum(ood_preds >= ood_thres)
    FN = np.sum(ood_preds < ood_thres)
    TPR = round(TP / (TP + FN), 3)   

    plot_parity(ax, data["in_dist"]["gt"], data["in_dist"]["preds"], mae_id, 'dimgrey', 'ID')
    plot_parity(ax, data["ood"]["gt"], data["ood"]["preds"], mae_ood, 'tomato', 'OOD')
    ax.scatter([], [], label=f'TPR: {TPR}', color='none')
    ax.axline((ood_gt.min(),0), (ood_gt.min(),1), linewidth=2, color='tomato')
    ax.axline((0, ood_gt.min()), (1, ood_gt.min()), linewidth=2, color='tomato')
    ax.set_xlabel(f'Ground Truth {x_label}', fontsize=26)
    ax.tick_params(axis='both', labelsize=16)
    ax.set_ylabel(f'Predicted {x_label}', fontsize=26)
    # Dynamically set limits based on data
    set_plot_limits(ax, gt_bilinear_id, gt_bilinear_ood)
    title_name = method
    ax.set_title(f'{title_name} Parity Plot', fontsize=34)
    ax.legend(loc='upper left', fontsize=26)

    plt.tight_layout()
    plt.savefig(osp.join(logdir, f'parity_plot.png'), bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"parity plot saved at: {osp.join(logdir, f'parity_plot.png')}")


def plot_correlations(path, model_type='bilinear', EPS=1e-10):
    """
    Plots scatter plot -- predictions vs ground truth and 
    computes pearson and spearman correlations, R-squared and KL divergence.
    """
    for eval_type in ['in_dist', 'ood']:
        # load data
        res_pth = osp.join(path, f'{model_type}_eval_{eval_type}.pkl')
        with open(res_pth, "rb") as input_file:
            res = pkl.load(input_file)
        preds = res['preds']
        gt = res['gt']   

        # format plot 
        plt.close('all')
        plt.figure()
        plt.scatter(gt, preds)
        plt.axline((0, 0), (1, 1), linewidth=1, color='r')
        plt.xlabel('gt')
        plt.ylabel('pred')

        # compute correlatios
        pearson_coeff = pearsonr(preds.squeeze(), gt.squeeze())
        spearman_coeff = spearmanr(preds.squeeze(), gt.squeeze())
        r_squared = r2_score(gt.squeeze(), preds.squeeze())
        bins = np.linspace(min(gt.min(), preds.min()), max(gt.max(), preds.max()), 100)
        hist_gt, _ = np.histogram(gt.squeeze(), bins=bins, density=True)
        hist_preds, _ = np.histogram(preds.squeeze(), bins=bins, density=True)
        hist_gt_normalized = hist_gt / np.sum(hist_gt)
        hist_preds_normalized = hist_preds / np.sum(hist_preds)
        kl_divergence = np.sum(kl_div(hist_gt_normalized+EPS, hist_preds_normalized+EPS)) #lower better [0,inf]
        
        # save plot
        plt.title(f'pearson stat: {round(pearson_coeff.statistic,2)}, pval: {round(pearson_coeff.pvalue,2)}\n \
                    spearman stat: {round(spearman_coeff.statistic,2)}, pval: {round(spearman_coeff.pvalue,2)}\n \
                    r_squared: {round(r_squared,2)}\n \
                    kl_div: {round(kl_divergence,2)}')
        plt.savefig(osp.join(path, f'{eval_type}_corr.png'), bbox_inches='tight', dpi=300)
        results_path = os.path.join(path, f'{eval_type}_results.txt')
        with open(results_path, 'a') as f:
            f.write(f'Evaluation Type: {eval_type}\n')  # Write evaluation type
            f.write(f'pearson: {round(pearson_coeff.statistic,2)}, spearman: {round(spearman_coeff.statistic,2)}, r2: {round(r_squared,2)}, kl_div: {round(kl_divergence,2)}')  # Write mean and sem result
            f.write('\n')


def get_filename(benchmark, prop):
    # Build the filename
    filename_parts = [f'{prop}']
    if benchmark == 'matbench':
        filename_parts.append('magpie')
    elif benchmark == 'mp' or benchmark == 'aflow':
        filename_parts.append('oliynyk')
    elif benchmark == 'moleculenet':
        filename_parts.append('rdkit')
    # Join the parts with underscores
    filename = '_'.join(filename_parts) + '.pkl'
    return filename


if __name__ == "__main__":

    benchmarks = ['aflow']*6 + ['matbench']*3 + ['mp']*3 + ['moleculenet']*4
    props = ['Egap', 'bulk_modulus_vrh', 'debye_temperature', 'shear_modulus_vrh', 'thermal_conductivity_300K', 'thermal_expansion_300K', \
            'band_gap', 'refractive_ind', 'yield_strength', \
            'bulk_modulus', 'elastic_anisotropy', 'shear_modulus', \
            'bace', 'delaney', 'freesolv', 'lipo']

    for benchmark, prop in zip(benchmarks, props):

        path = os.path.join('log', f'{benchmark}', f'{prop}')

        x_label, title = get_prop_labels(prop)

        eval_data = load_eval_data(prop, path)
        kde_dist(path, eval_data, prop, x_label)
        parity_plot(eval_data, prop, path, x_label)
        plot_correlations(path)

        filename = get_filename(benchmark, prop)
        datapath = osp.join('data', f'{benchmark}', f'{prop}', f'demos_{filename}.pkl')
        tsne_plot(path, datapath)
