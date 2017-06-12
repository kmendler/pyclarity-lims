import pkg_resources

try:
    __version__ = pkg_resources.get_distribution("pyclarity_lims").version
except pkg_resources.DistributionNotFound:
    __version__ = ""
