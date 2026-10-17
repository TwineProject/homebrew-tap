cask "twine-ade" do
  version "0.3.3"
  sha256 "e5bc3f6714f2ecf59d4c3576c16eac66a4d81f01bb640e18719ee77ce208652b"

  url "https://github.com/standing-desks/twine/releases/download/v#{version}/Twine-#{version}-macos-arm64.dmg"
  name "Twine"
  desc "Agent development environment for coordinating coding agents"
  homepage "https://github.com/standing-desks/twine"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on arch: :arm64
  depends_on macos: :tahoe

  app "Twine.app"

  # Twine's saved sessions, transcripts, and workflows are user data.
  # No zap stanza required.
end
