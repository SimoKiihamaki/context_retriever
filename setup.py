import os
from setuptools import setup, find_packages

# Read the content of the README file
with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="code-context-retriever",
    version="1.0.0",
    description="Retrieve context from code repositories using DSPy and embeddings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    license="MIT",
    url="https://github.com/yourusername/code-context-retriever",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "dspy-ai>=2.0.0",
        "numpy>=1.20.0",
        "pyyaml>=5.1",
        "tqdm>=4.0.0",
    ],
    extras_require={
        "faiss": ["faiss-cpu>=1.7.0"],
        "dev": [
            "pytest>=6.0.0",
            "pylint>=2.5.0",
            "black>=21.5b2",
            "mypy>=0.800",
        ],
        "api": [
            "fastapi>=0.68.0",
            "uvicorn>=0.15.0",
            "pydantic>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "code-context-retriever=code_context_retriever.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="dspy, retrieval, code, context, embeddings, ai, nlp",
)