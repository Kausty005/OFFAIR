import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "192.168.88.188",
    "192.168.88.188:5000",
    "172.23.160.1",
    "172.23.160.1:5000",
    "localhost",
    "localhost:5000",
    "127.0.0.1",
    "127.0.0.1:5000",
  ],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
