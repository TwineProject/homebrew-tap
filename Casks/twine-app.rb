cask "twine-app" do
  version "0.2.1"
  sha256 "313b3d9b8bd5698395ab537eada7b33bab631edfb871718c57b2bd00a53af1a9"

  url "https://github.com/aravind-n/twine/releases/download/v#{version}/Twine-#{version}-macos-arm64.dmg"
  name "Twine"
  desc "Workspace for coordinating coding agents"
  homepage "https://github.com/aravind-n/twine"

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
