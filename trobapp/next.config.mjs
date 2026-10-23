/** @type {import('next').NextConfig} */
// /api/v1/* is proxied at runtime by src/app/api/v1/[...path]/route.ts (BACKEND_API_URL).
const nextConfig = {
  reactStrictMode: false,
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
