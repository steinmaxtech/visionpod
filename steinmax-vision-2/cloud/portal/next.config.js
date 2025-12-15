/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // API proxy for development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.API_URL 
          ? `${process.env.API_URL}/api/v1/:path*`
          : 'http://localhost:8000/api/v1/:path*',
      },
    ]
  },
}

module.exports = nextConfig
