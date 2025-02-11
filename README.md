# HTTP/HTTPS Proxy Rotator with User-Agent Cycling

A lightweight Python proxy that automatically rotates User-Agent headers for each request. This tool acts as a local proxy server that sits between your application and the internet, cycling through different User-Agent strings to help prevent request patterns from being too uniform.

# Features

- Supports both HTTP and HTTPS traffic
- Sequential rotation through a list of common User-Agent strings
- Configurable listening port
- Verbose logging mode for debugging
- Thread-safe User-Agent rotation
- Zero external proxy requirements - runs completely locally

# Requirements

```
pip install http-parser
```
# Usage
Basic usage:
```
python rotator.py -p <port> -v
```
![image](https://github.com/user-attachments/assets/16ddfb03-edb6-4cac-b8b4-e7a61c346874)

# Use Cases

- Testing how websites respond to different User-Agents
- Preventing rate limiting based on User-Agent patterns
