/** @type {import('next').NextConfig} */
const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000'

const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${pythonBackendUrl}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
