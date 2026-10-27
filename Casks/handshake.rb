cask "handshake" do
  version "0.4.2"
  sha256 "58a8047c3a9cd0a476c77e6ce4745be482b04c86bc42eabe955df48bb1b281b4"

  url "https://github.com/standing-desks/handshake/releases/download/v#{version}/Handshake-#{version}-macos-arm64.dmg"
  name "Handshake"
  desc "Agent development environment for coordinating coding agents"
  homepage "https://github.com/standing-desks/handshake"

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
