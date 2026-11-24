param(
    [Parameter(Mandatory=$true)][string]$SrcPath,
    [Parameter(Mandatory=$true)][string]$DstPath
)

Add-Type -AssemblyName System.Drawing

$csharp = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class VignetteFeatherV2
{
    public static void Process(string srcPath, string dstPath, int quality)
    {
        using (Bitmap srcOrig = new Bitmap(srcPath))
        using (Bitmap bmp = new Bitmap(1408, 768, PixelFormat.Format24bppRgb))
        {
            using (Graphics g = Graphics.FromImage(bmp))
            {
                g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                g.DrawImage(srcOrig, 0, 0, 1408, 768);
            }

            int w = bmp.Width;
            int h = bmp.Height;
            BitmapData data = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadWrite, PixelFormat.Format24bppRgb);
            int stride = data.Stride;
            byte[] buf = new byte[stride * h];
            Marshal.Copy(data.Scan0, buf, 0, buf.Length);

            // Sample inner paper background near (w*0.22, h*0.12) so there is zero seam between inner paper and outer margin
            int sampleX = (int)(w * 0.22);
            int sampleY = (int)(h * 0.12);
            int sIdx = sampleY * stride + sampleX * 3;
            double creamB = buf[sIdx];
            double creamG = buf[sIdx + 1];
            double creamR = buf[sIdx + 2];

            double cx = w / 2.0;
            double cy = h / 2.0;
            double rx = w * 0.43;
            double ry = h * 0.45;

            for (int y = 0; y < h; y++)
            {
                double ny = (y - cy) / ry;
                double ny2 = ny * ny;
                int rowOffset = y * stride;

                for (int x = 0; x < w; x++)
                {
                    int idx = rowOffset + x * 3;
                    double bIn = buf[idx];
                    double gIn = buf[idx + 1];
                    double rIn = buf[idx + 2];

                    // 1. Normalize any near-paper background tint (removes any faint inner canvas box from generator)
                    double diff = Math.Abs(rIn - creamR) + Math.Abs(gIn - creamG) + Math.Abs(bIn - creamB);
                    if (diff < 22.0)
                    {
                        double paperBlend = diff / 22.0;
                        paperBlend = paperBlend * paperBlend * (3.0 - 2.0 * paperBlend);
                        rIn = rIn * paperBlend + creamR * (1.0 - paperBlend);
                        gIn = gIn * paperBlend + creamG * (1.0 - paperBlend);
                        bIn = bIn * paperBlend + creamB * (1.0 - paperBlend);
                    }

                    // 2. Smooth elliptical radial vignette fade to uniform cream paper
                    double nx = (x - cx) / rx;
                    double r = Math.Sqrt(nx * nx + ny2);
                    double alpha = 1.0;
                    if (r >= 1.0) alpha = 0.0;
                    else if (r > 0.68)
                    {
                        double t = (1.0 - r) / (1.0 - 0.68);
                        alpha = t * t * (3.0 - 2.0 * t);
                    }

                    buf[idx]     = (byte)Math.Round(bIn * alpha + creamB * (1.0 - alpha));
                    buf[idx + 1] = (byte)Math.Round(gIn * alpha + creamG * (1.0 - alpha));
                    buf[idx + 2] = (byte)Math.Round(rIn * alpha + creamR * (1.0 - alpha));
                }
            }

            Marshal.Copy(buf, 0, data.Scan0, buf.Length);
            bmp.UnlockBits(data);

            ImageCodecInfo jpgEncoder = null;
            foreach (ImageCodecInfo codec in ImageCodecInfo.GetImageEncoders())
            {
                if (codec.MimeType == "image/jpeg") { jpgEncoder = codec; break; }
            }
            EncoderParameters ep = new EncoderParameters(1);
            ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, (long)quality);
            bmp.Save(dstPath, jpgEncoder, ep);
        }
    }
}
"@

Add-Type -TypeDefinition $csharp -ReferencedAssemblies System.Drawing

foreach ($q in @(84, 78, 72, 66)) {
    [VignetteFeatherV2]::Process($SrcPath, $DstPath, $q)
    $size = (Get-Item $DstPath).Length
    if ($size -le 295000) {
        Write-Host ("Saved {0} ({1:N1} KB, q={2})" -f $DstPath, ($size / 1024.0), $q)
        break
    }
}
