import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0a0a",
        }}
      >
        <div
          style={{
            width: 90,
            height: 90,
            borderRadius: 999,
            border: "8px solid #7fd6a8",
            display: "flex",
          }}
        />
      </div>
    ),
    size
  );
}
