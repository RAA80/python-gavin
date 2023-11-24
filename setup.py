#! /usr/bin/env python3

from distutils.core import setup

setup(name="python-gavin",
      version="0.0.2",
      description="GST Gavin camera module",
      url="https://github.com/RAA80/python-gavin",
      author="Alexey Ryadno",
      author_email="aryadno@mail.ru",
      license="MIT",
      packages=["gavin", "gavin.libs"],
      package_data={"gavin": ["libs/x64/*.dll", "libs/x86/*.dll"]},
      install_requires=["numpy >= 1.12", "opencv-python >= 3"],
      scripts=["scripts/gavin-server", "scripts/gavin-gui"],
      platforms=["Windows"],
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Science/Research",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: MIT License",
                   "Operating System :: Microsoft :: Windows",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.5",
                   "Programming Language :: Python :: 3.6",
                   "Programming Language :: Python :: 3.7",
                   "Programming Language :: Python :: 3.8",
                   "Programming Language :: Python :: 3.9",
                  ],
     )
