cask "handshake" do
  version "0.9.0"
  sha256 "b18eedec343bca9506d60dc15895f6d363e5ee0e3db739fec65ccef915148bf9"

  url "https://github.com/standing-desks/handshake/releases/download/v#{version}/Handshake-#{version}-macos-arm64.dmg"
  name "Handshake"
  desc "Agent development environment for coordinating coding agents"
  homepage "https://standing-desks.github.io/handshake/"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on arch: :arm64
  depends_on macos: :tahoe

  app "Handshake.app"

  # Handshake's saved sessions, transcripts, and workflows are user data.
  # No zap stanza required.
end
