# Mappero 🚀

**Mappero** is a 3D capture, mapping, and reconstruction project that unifies various photogrammetry software and packages into a single toolset, simplifying 3D modeling, visual localization, and mapping workflows.

## Table of Contents 📑

- [Support and Features](#support-and-features)
- [Installation](#installation)
- [Usage](#usage)
  - [Workspace](#workspace)
  - [Colmap](#colmap)
  - [Glomap](#glomap)
  - [Visualization](#visualization)
- [Running with Docker](#running-with-docker)

## Support and Features 🛠️

- **Support**: Integrates popular photogrammetry tools:
  - **COLMAP**: Structure-from-Motion and Multi-View Stereo
  - **GLomap**: Global Localization Mapping
- 3D visualization based on **Open3D**

## Installation 🖥️

### Prerequisites

- Python 3.8+
- Git
- Docker (optional for containerized deployment)
- Required Python packages (specified in `pyproject.toml`)

### Clone the Repository

1. Clone the repository:

   ```bash
   git clone https://github.com/Tarekbouamer/mappero.git
   cd mappero
   ```

2. Install dependencies:

   ```bash
   ./install_cmake.sh
   ./install_colmap.sh
   ./install_glomap.sh
   ```

3. Install Mappero:

   ```bash
   pip install --upgrade pip
   pip install -ve .
   ```

## Usage

### Workspace

Mappero follows the same structure as Colmap for workspace setup. The workspace should contain the following directories:

- `images`: Contains the images to be processed.
- `sparse`: Contains the sparse reconstruction results.

### Colmap

To run Colmap:

```bash
mappero-colmap /path/to/data/south-building
```

For more options and information, use the help flag:

```bash
mappero-colmap -h
```

### Glomap

To run Glomap:

```bash
mappero-glomap /path/to/data/south-building
```

For more options and information, use the help flag:

```bash
mappero-glomap -h
```

### Visualization

To visualize the results:

```bash
mappero-vis --model /path/to/data/south-building/sparse/0
```

For more visualization options, use the help flag:

```bash
mappero-vis -h
```

## Running with Docker 🐳

### Build the Docker Image

```bash
# build the docker image
docker build -t mappero .
```

### Run the Docker Container

```bash
# run the docker container
# specify the path to the directory containing the images to be processed
docker run -it -v /path/to/your/data:/mnt/data mappero
```