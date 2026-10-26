cask "handshake" do
  version "0.4.1"
  sha256 "0b498cbd32f0526f01c693749bc55f853bc715c802df749648dc0be466025af9"

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
