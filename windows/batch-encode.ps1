# Encodes any video with first video-stream height >= 1080 to AV1+Opus (1080p),
# writing output next to the input as: "<name> av1<ext>"
# Requires ffprobe + ffmpeg in PATH.

$ext = @("mp4","mkv","mov","m4v","webm","avi","ts","m2ts","mts","wmv","flv","3gp")

Get-ChildItem -Path . -Recurse -File |
  Where-Object { $ext -contains $_.Extension.TrimStart('.').ToLower() } |
  ForEach-Object {

    $inFile = $_.FullName

    # Skip files that already look like outputs
    if ($_.BaseName -like "* av1") { return }

    # Probe codec, height, and frame rate of first video stream
    $probe = & ffprobe -v error -select_streams v:0 `
      -show_entries stream=codec_name,height,r_frame_rate `
      -of default=nokey=1:noprint_wrappers=1 "$inFile" 2>$null

    $codec = $probe | Select-Object -First 1
    $h = $probe | Select-Object -Skip 1 -First 1
    $rate = $probe | Select-Object -Skip 2 -First 1

    if ($codec -eq "av1") {
      Write-Host "SKIP (already AV1): $inFile"
      return
    }

    if (!($h -match '^\d+$')) { return }

    if ([int]$h -ge 1080) {
      # Parse frame rate (e.g., 30000/1001) into numeric fps
      $fps = 0.0
      if ($rate -match '^(\d+)\s*/\s*(\d+)$') {
        $fps = [double]$matches[1] / [double]$matches[2]
      }

      $is4k = ([int]$h -ge 2160)
      $is60 = ($fps -ge 50.0)

      if ($is4k -and $is60) {
        $maxrateK = 28000
      } elseif ($is4k) {
        $maxrateK = 18000
      } elseif ($is60) {
        $maxrateK = 10000
      } else {
        $maxrateK = 6000
      }

      $bufsizeK = $maxrateK * 2

      $outFile = Join-Path $_.DirectoryName ($_.BaseName + " av1" + $_.Extension)

      # Skip if output already exists
      if (Test-Path -LiteralPath $outFile) {
        Write-Host "SKIP (exists): $outFile"
        return
      }

      Write-Host ("ENCODE ({0}p @ {1:N2} fps, maxrate {2}k): {3}" -f $h, $fps, $maxrateK, $inFile)
      Write-Host " -> $outFile"

      & ffmpeg -hide_banner -y -i "$inFile" `
        -map 0:v:0 -map 0:a:0 `
        -c:v libsvtav1 -preset 3 -crf 24 -maxrate ${maxrateK}k -bufsize ${bufsizeK}k -g 240 -pix_fmt yuv420p10le `
        -c:a libopus -b:a 128k -movflags +faststart `
        "$outFile"
    }
  }
