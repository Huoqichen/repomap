const allowedDevOrigins = (process.env.ALLOWED_DEV_ORIGINS || "localhost,127.0.0.1,192.168.164.1")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  allowedDevOrigins
};

export default nextConfig;
