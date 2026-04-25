import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
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
            width: 16,
            height: 16,
            borderRadius: 999,
            border: "2px solid #7fd6a8",
            display: "flex",
          }}
        />
      </div>
    ),
    size
  );
}
