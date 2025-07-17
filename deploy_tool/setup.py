from setuptools import setup, find_packages

setup(
    name="deploy-tool",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
        "boto3",
        "gitpython",
        "cryptography",
    ],
    entry_points="""
        [console_scripts]
        deploy-tool=deploy_tool.cli:cli
    """,
    python_requires=">=3.6",
    author="Author",
    author_email="author@example.com",
    description="A CLI tool for deploying static sites to AWS",
    keywords="aws, deployment, static-site",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
