cask "twine-ade" do
  version "0.3.1"
  sha256 "4e4c5458e18e7006bd08d63b1c8f04fe0a025fd7f290077e00e1b93cc5c68212"

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
