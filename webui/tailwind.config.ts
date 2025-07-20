import { type Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";

export const PAGE_WIDTH = 960;

export default {
  darkMode: 'class',
  content: ["./src/**/*.tsx"],
  theme: {
    extend: {
      width: {
        page: `${PAGE_WIDTH}px`,
      },
      minWidth: {
        page: `${PAGE_WIDTH}px`,
      },
      maxWidth: {
        page: `${PAGE_WIDTH}px`,
      },
      colors: {
        primary: "#1D4ED8", // 深蓝色
        secondary: "#E0F2FE", // 浅蓝背景
        accent: "#2563EB",
      },
      textColor: {
        default: "#1E3A8A", // 深蓝文字
        button: "#ffffff",
        "button-hover": "#ffffff",
      },
      backgroundColor: {
        body: "#ffffff", // 白底
        button: "#1D4ED8", // 蓝色按钮
        "button-hover": "#2563EB", // hover 更亮
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", ...fontFamily.sans],
      },
    },
  },
  plugins: [],
} satisfies Config;
