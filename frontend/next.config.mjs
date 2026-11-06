const dev = process.env.NODE_ENV === 'development';

/** @type {import('next').NextConfig} */
const nextConfig = dev
  ? {
      // Dev only: proxy API calls to the FastAPI backend.
      async rewrites() {
        return [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }];
      },
    }
  : { output: 'export', images: { unoptimized: true }, trailingSlash: false };

export default nextConfig;
