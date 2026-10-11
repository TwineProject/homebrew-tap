cask "twine-ade" do
  version "0.3.0"
  sha256 "5ae77a76a28798ae6911d30ea43aace9ab7039f781c871e85e1570cb80df4131"

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
