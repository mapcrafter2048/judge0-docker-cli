FROM node:18-slim

# Create non-root user
RUN useradd -m -s /bin/bash judge

# Install security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /tmp

# Switch to non-root user
USER judge

# Default command
CMD ["/bin/bash"]
