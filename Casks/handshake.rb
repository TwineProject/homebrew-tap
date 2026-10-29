cask "handshake" do
  version "0.6.0"
  sha256 "04fdd0a72a775b22081d168a738e1ac9985afc8308374cf6b9ee4d28bbea4954"

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
