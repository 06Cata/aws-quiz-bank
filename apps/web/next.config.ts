import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [
          {
            type: "host",
            value: "aws-quiz-bank-web.vercel.app"
          }
        ],
        destination: "https://datavoyageio.com/:path*",
        permanent: true
      }
    ];
  }
};

export default nextConfig;
