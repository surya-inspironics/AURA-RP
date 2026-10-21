/** @type {import('next').NextConfig} */
const pythonBackendUrl = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8000'

const nextConfig = {
  images: {
    unoptimized: true,
  },

  async rewrites() {
    return [
      {
        source: '/api/v1/cases',
        destination: `${pythonBackendUrl}/api/v1/cases/`,
      },
      {
        source: '/api/v1/evidence',
        destination: `${pythonBackendUrl}/api/v1/evidence/`,
      },
      {
        source: '/api/v1/decisions',
        destination: `${pythonBackendUrl}/api/v1/decisions/`,
      },
      {
        source: '/api/v1/team',
        destination: `${pythonBackendUrl}/api/v1/team/`,
      },
      {
        source: '/api/v1/audit',
        destination: `${pythonBackendUrl}/api/v1/audit/`,
      },
      {
        source: '/api/v1/integrations',
        destination: `${pythonBackendUrl}/api/v1/integrations/`,
      },
      {
        source: '/api/v1/:path*',
        destination: `${pythonBackendUrl}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
