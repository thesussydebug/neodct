################################################################################
#
# python-miniaudio
#
################################################################################

PYTHON_MINIAUDIO_VERSION = 1.71
PYTHON_MINIAUDIO_SOURCE = miniaudio-$(PYTHON_MINIAUDIO_VERSION).tar.gz
PYTHON_MINIAUDIO_SITE = https://files.pythonhosted.org/packages/d8/d5/e5439dc08561f73656bfeb3340fc64ab63163e101426593d8fb9a025ff1e
PYTHON_MINIAUDIO_SETUP_TYPE = setuptools
PYTHON_MINIAUDIO_LICENSE = MIT
PYTHON_MINIAUDIO_LICENSE_FILES = LICENSE
PYTHON_MINIAUDIO_DEPENDENCIES = host-python-cffi python-cffi

$(eval $(python-package))
