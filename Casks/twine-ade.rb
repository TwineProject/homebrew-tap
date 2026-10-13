cask "twine-ade" do
  version "0.3.2"
  sha256 "ed047e3463f436ab7c4def864ff9b83a6c852ab0b2f938d3c208e48c4ac3f230"

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
