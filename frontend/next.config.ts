import type { NextConfig } from "next";
import os from "os";

function getLocalIpAddresses() {
  const ips: string[] = [];
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name] || []) {
      if (iface.family === "IPv4" && !iface.internal) {
        ips.push(iface.address);
        ips.push(`${iface.address}:5000`);
      }
    }
  }
  return ips;
}

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "localhost",
    "localhost:5000",
    "127.0.0.1",
    "127.0.0.1:5000",
    "0.0.0.0",
    "0.0.0.0:5000",
    ...getLocalIpAddresses(),
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
